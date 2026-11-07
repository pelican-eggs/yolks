"""Wings entry point for the AMP-derived Farming Simulator 25 server."""

from contextlib import contextmanager, suppress
import ipaddress
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from xml.etree import ElementTree as ET

from common import (GAME, PROFILE, ROOT, Failure, atomic_file, compat, product_key, proton, proton_env,
                    run_proton, secret, stop_wine, terminate, xvfb)
from dlc import activate_configured, prepare_for_reinstall
from install import drop_volume_root, install, installed
from web import Forms, Web, start_payload


READY = "FS25 web interface ready"
GAME_READY = "FS25 game server started"


class StopFlag:
    # The signal handler only changes a flag; it must not take a thread lock.
    stopped = False

    def set(self):
        self.stopped = True

    def is_set(self):
        return self.stopped

    def wait(self, seconds):
        if not self.stopped:
            time.sleep(seconds)
        return self.stopped


STOP = StopFlag()


def port(variable, fallback):
    value = os.environ.get(variable, "").strip() or str(fallback)
    if not re.fullmatch(r"[0-9]{1,5}", value) or not 1024 <= int(value) <= 65535:
        raise Failure(f"{variable} must be a port between 1024 and 65535.")
    return int(value)


def flag(variable, default):
    value = os.environ.get(variable, "") or default
    if value not in ("true", "false"):
        raise Failure(f"{variable} must be true or false.")
    return value == "true"


def load_xml(path):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    try:
        return ET.parse(path, parser=parser)
    except ET.ParseError:
        raise Failure(f"Invalid XML in {path.name}; the file was left untouched.") from None


def save_xml(document, path):
    with atomic_file(path, "wb") as out:
        document.write(out, encoding="utf-8", xml_declaration=True)


def prepare_profile(tag, env):
    user = compat(tag) / "pfx" / "drive_c" / "users" / "steamuser"
    if not user.is_dir():
        print("Creating the GE-Proton prefix.")
        with xvfb() as display:
            prefix_env = dict(env, DISPLAY=display)
            process = run_proton(tag, "cmd", "/c", "exit", env=prefix_env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 90
                while process.poll() is None and not STOP.wait(0.25):
                    if time.monotonic() >= deadline:
                        raise Failure("GE-Proton prefix initialization timed out.")
                if STOP.is_set():
                    raise Failure("GE-Proton prefix initialization stopped.")
                if process.returncode != 0:
                    raise Failure("GE-Proton failed to initialize its prefix.")
            finally:
                terminate(process)
                stop_wine(tag, prefix_env)
    if not user.is_dir():
        raise Failure("GE-Proton did not create the steamuser profile.")

    docs = (user / "Documents").resolve()
    if not docs.is_relative_to(ROOT.resolve()):
        raise Failure("Wine Documents points outside the persistent server volume.")
    docs.mkdir(parents=True, exist_ok=True)
    origin = docs / "My Games" / "FarmingSimulator2025"
    origin.parent.mkdir(parents=True, exist_ok=True)
    PROFILE.mkdir(exist_ok=True)
    if origin.is_symlink():
        if origin.resolve() != PROFILE.resolve():
            origin.unlink()
    elif origin.is_dir():
        # Only import files that are not already present in the persistent profile.
        for source in sorted(origin.rglob("*")):
            target = PROFILE / source.relative_to(origin)
            if source.is_symlink():
                if not target.exists() and not target.is_symlink():
                    target.symlink_to(source.readlink())
            elif source.is_dir():
                target.mkdir(exist_ok=True)
            elif not target.exists():
                shutil.copy2(source, target)
        shutil.rmtree(origin)
    if not origin.exists():
        origin.symlink_to(PROFILE, target_is_directory=True)
    logs = PROFILE / "dedicated_server" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    if not (ROOT / "logs").exists() and not (ROOT / "logs").is_symlink():
        (ROOT / "logs").symlink_to(logs.relative_to(ROOT), target_is_directory=True)
    return logs


def configure_web(web_port, tls_port, tls_on, username, password):
    path = GAME / "dedicatedServer.xml"
    document = load_xml(path)
    root = document.getroot()
    webserver = root if root.tag == "webserver" else root.find(".//webserver")
    tls = root.find(".//tls")
    user = root.find(".//username")
    if webserver is None or tls is None or user is None:
        raise Failure("Unexpected layout of dedicatedServer.xml.")
    webserver.set("port", str(web_port))
    tls.set("port", str(tls_port))
    tls.set("active", "true" if tls_on else "false")
    user.text = username
    parents = {child: parent for parent in root.iter() for child in parent}
    container = parents[user]
    node = container.find("passphrase")
    legacy = container.find("password")
    if node is None:
        if legacy is None:
            node = ET.SubElement(container, "passphrase")
        else:
            node = legacy
            node.tag = "passphrase"
    if legacy is not None and legacy is not node:
        container.remove(legacy)
    if password:
        node.text = password
    save_xml(document, path)


def configure_game_port(game_port):
    path = PROFILE / "dedicated_server" / "dedicatedServerConfig.xml"
    if not path.exists():
        return False
    document = load_xml(path)
    entries = list(document.getroot().iter("port"))
    if not entries:
        return False
    for entry in entries:
        entry.text = str(game_port)
    save_xml(document, path)
    return True


def web_password():
    document = load_xml(GAME / "dedicatedServer.xml")
    user = document.find(".//username")
    if user is not None:
        for parent in document.iter():
            if user in list(parent):
                return parent.findtext("passphrase") or parent.findtext("password") or ""
    return ""


def activate(tag, env):
    activation = PROFILE / "AHC_63805.dat"
    if activation.is_file() and activation.stat().st_size:
        print("FS25 activation data is already present.")
        return
    key = product_key()
    if not key:
        raise Failure("Set GIANTS Product Key in the server's Admin Startup settings before starting.")
    print("Opening the official GIANTS activation dialog.")
    with xvfb() as display:
        gui = dict(env, DISPLAY=display)
        launcher = run_proton(tag, GAME / "FarmingSimulator2025.exe", env=gui, cwd=GAME,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline and not STOP.is_set():
                if activation.is_file() and activation.stat().st_size:
                    return
                result = subprocess.run(["xdotool", "search", "--onlyvisible", "--name",
                                         "Product Key|FarmingSimulator2025"],
                                        env=gui, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, timeout=5)
                windows = result.stdout.splitlines()
                if windows:
                    window = windows[0]
                    break
                STOP.wait(2)
            else:
                raise Failure("FS25 activation dialog did not appear.")

            def xdo(*args, **kwargs):
                return subprocess.run(["xdotool", *args], env=gui, check=True, timeout=15,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)

            xdo("windowraise", window)
            xdo("windowfocus", window)
            xdo("type", "--clearmodifiers", "--delay", "40", "--file", "-", input=key.encode())
            xdo("key", "--clearmodifiers", "Return")
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline and not STOP.is_set():
                if activation.is_file() and activation.stat().st_size:
                    print("GIANTS activation successful.")
                    return
                STOP.wait(2)
            raise Failure("GIANTS activation did not complete. Check the key and its activation limit.")
        finally:
            terminate(launcher)
            stop_wine(tag, gui)


def endpoints(web_port, tls_port, tls_on):
    addresses = ["127.0.0.1"]
    with suppress(OSError):
        addresses.extend(answer[4][0] for answer in socket.getaddrinfo(
            socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM))
    addresses = [address for address in dict.fromkeys(addresses)
                 if not ipaddress.IPv4Address(address).is_unspecified]
    if tls_on:
        return [Web(f"https://{host}:{tls_port}", GAME / "cert.pem") for host in addresses]
    return [Web(f"http://{host}:{web_port}") for host in addresses]


def web_ready(candidates, process):
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline and process.poll() is None and not STOP.is_set():
        for client in candidates:
            if STOP.is_set():
                return None
            try:
                client.request()
                print(READY)
                return client
            except (OSError, ValueError):
                pass
        STOP.wait(2)
    return None


def overrides():
    def setting(name):
        return os.environ.get("FS25_" + name, "")

    return {
        "savegame": setting("SAVEGAME"),
        "game_name": setting("SERVER_NAME"),
        "game_password": secret("game-password", trim=False),
        "admin_password": secret("ingame-admin-password", trim=False),
        "max_player": setting("MAX_PLAYERS"),
        "mp_language": setting("LANGUAGE"),
        "auto_save_interval": setting("AUTOSAVE"),
        "stats_interval": setting("STATS_INTERVAL"),
        "pause_game_if_empty": setting("PAUSE_EMPTY"),
        "crossplay_allowed": setting("CROSSPLAY"),
    }


def autostart(client, username, password, game_port, port_configured, values, process):
    page = client.login(username, password)
    if page.find("stop_server"):
        print(GAME_READY)
        return
    form = page.find("start_server")
    if form is None:
        raise Failure("FS25 web login or game start form was not accepted.")
    if "server_port" not in form.controls and not port_configured and game_port != 10823:
        raise Failure("Set the allocated game port in the FS25 web interface before starting the game.")
    client.request(start_payload(form, game_port, values), timeout=8)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and process.poll() is None and not STOP.is_set():
        if Forms(client.request()).find("stop_server"):
            print(GAME_READY)
            return
        STOP.wait(2)
    if not STOP.is_set():
        raise Failure("FS25 did not report a running game. Check the web interface and logs.")


def stop_game(client, username, password):
    page = client.login(username, password, timeout=2)
    form = page.find("stop_server")
    if form is None:
        if page.find("start_server") is None:
            print("FS25 web stop skipped: the web login did not succeed.")
        return
    client.request(form.payload(stop_server="Stop"), timeout=3)
    deadline = time.monotonic() + 7
    while time.monotonic() < deadline:
        if Forms(client.request(timeout=2)).find("start_server"):
            print("FS25 game server stopped through the web interface.")
            return
        time.sleep(0.5)
    print("FS25 web stop has not been confirmed.")


def follow_logs(directory, process):
    offsets = {}
    while process.poll() is None and not STOP.is_set():
        for path in sorted(directory.glob("server*.log")):
            try:
                with path.open("rb") as log:
                    info = os.fstat(log.fileno())
                    key = (info.st_dev, info.st_ino)
                    offset = offsets.get(key, 0)
                    if offset > info.st_size:
                        offset = 0
                    log.seek(offset)
                    data = log.read(65536)
                    complete = data.rfind(b"\n") + 1
                    if complete:
                        print(data[:complete].decode("utf-8", "replace").rstrip("\r\n"))
                    elif len(data) == 65536:
                        complete = len(data)
                        print(data.decode("utf-8", "replace"))
                    offsets[key] = offset + complete
            except (FileNotFoundError, IsADirectoryError):
                pass
        STOP.wait(1)


@contextmanager
def interruptible_install(exit_code):
    # An install may be doing a long download or waiting for Setup.exe. Interrupt it
    # immediately so installer cleanup and rollback run before Wings forces a stop.
    def cancel(*_):
        sys.exit(exit_code)

    handlers = {sig: signal.signal(sig, cancel) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        yield
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)


def run_install(*, require_game=False):
    with interruptible_install(0 if require_game else 143):
        install(require_game=require_game)
        if not require_game and installed():
            prepare_for_reinstall()


def ensure_installed():
    state = installed()
    if not state:
        print("No complete FS25 installation found. Preparing it before starting.")
        run_install(require_game=True)
        state = installed()
        if not state:
            raise Failure("FS25 installation did not complete; the dedicated server was not started.")
    else:
        print("Existing FS25 installation found. Skipping setup.")
    return state


def start():
    drop_volume_root()
    state = ensure_installed()
    tag = state["proton"]
    if not proton(tag).is_file() or not os.access(proton(tag), os.X_OK):
        raise Failure("The installed GE-Proton release is missing. Run Reinstall.")
    game_port, web_port, tls_port = port("SERVER_PORT", 10823), port("FS25_WEB_PORT", 8080), port("FS25_TLS_PORT", 8443)
    tls_on = flag("FS25_TLS", "false")
    if game_port == web_port or (tls_on and tls_port in (game_port, web_port)):
        raise Failure("The game, web and enabled TLS allocations must use distinct ports.")
    if tls_on and not all((GAME / name).is_file() for name in ("cert.pem", "pk.pem")):
        raise Failure("TLS requires game/cert.pem and game/pk.pem.")
    username = os.environ.get("FS25_ADMIN_USER", "").strip() or "admin"
    password = secret("web-admin-password", trim=False)
    auto = flag("FS25_AUTOSTART", "true")
    values = overrides() if auto else {}
    env = proton_env(tag)
    logs = prepare_profile(tag, env)
    configure_web(web_port, tls_port, tls_on, username, password)
    port_configured = configure_game_port(game_port)
    if not auto and not port_configured and game_port != 10823:
        print(f"Before starting the first game, set its port to {game_port} in the FS25 web interface.")
    activate(tag, env)
    if STOP.is_set():
        return 0
    with interruptible_install(0):
        activate_configured(tag, env)
    candidates = endpoints(web_port, tls_port, tls_on)
    process = run_proton(tag, GAME / "dedicatedServer.exe", env=env, cwd=GAME)
    client = None
    worker = threading.Thread(target=follow_logs, args=(logs, process), daemon=True)
    worker.start()
    try:
        client = web_ready(candidates, process)
        if client is None:
            if STOP.is_set():
                return 0
            raise Failure(f"FS25 did not bring up the web interface (Proton exit: {process.poll()}).")
        if auto and not STOP.is_set():
            try:
                autostart(client, username, password or web_password(), game_port,
                          port_configured, values, process)
            except (OSError, ValueError, Failure) as error:
                print(f"Game autostart failed: {error}. Start it in the FS25 web interface.", file=sys.stderr)
        while process.poll() is None and not STOP.wait(1):
            pass
        if STOP.is_set():
            return 0
        raise Failure(f"The dedicated server exited unexpectedly (Proton exit: {process.returncode}).")
    finally:
        if STOP.is_set() and client is not None and process.poll() is None:
            try:
                stop_game(client, username, password or web_password())
            except (OSError, ValueError, Failure):
                print("FS25 web stop failed; terminating the dedicated server.", file=sys.stderr)
        terminate(process)
        stop_wine(tag, env)
        worker.join(timeout=2)


def main():
    if sys.argv[1:] not in (["install"], ["start"]):
        print("Usage: server.py install|start", file=sys.stderr)
        return 2
    os.umask(0o077)
    try:
        if sys.argv[1] == "install":
            run_install()
            return 0
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: STOP.set())
        return start()
    except Failure as error:
        if STOP.is_set():
            return 0
        print(f"FS25: {error}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("FS25: a setup or runtime subprocess timed out.", file=sys.stderr)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # Never dump an HTTP body, private URL, input, or command line into the panel.
        print(f"FS25: {type(error).__name__}; check the server files and install logs.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
