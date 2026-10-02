#!/usr/bin/env python3
"""Farming Simulator 25 runtime helpers shipped inside the Pelican image."""

from __future__ import annotations

import argparse
import http.cookiejar
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


HOME = pathlib.Path(os.environ.get("FS25_HOME", "/home/container"))
PREFIX = pathlib.Path(os.environ.get("WINEPREFIX", str(HOME / ".fs25server")))
GAME_DIR = HOME / "game" / "Farming Simulator 2025"
CONFIG_DIR = HOME / "config" / "FarmingSimulator2025"
DEDICATED_DIR = CONFIG_DIR / "dedicated_server"
INSTALLER_DIR = HOME / "installer"
DLC_DIR = HOME / "dlc"
PDLC_DIR = CONFIG_DIR / "pdlc"
LOG_DIR = HOME / "logs"
DESKTOP_DIR = HOME / "Desktop"
SERVER_EXE = GAME_DIR / "dedicatedServer.exe"
GAME_EXE = GAME_DIR / "FarmingSimulator2025.exe"
WINE_GAME_DIR = PREFIX / "drive_c" / "Program Files (x86)" / "Farming Simulator 2025"
WINE_CONFIG_DIR = (
    PREFIX / "drive_c" / "users" / os.environ.get("USER", "container")
    / "Documents" / "My Games" / "FarmingSimulator2025"
)


def log(message: str) -> None:
    print(f"[FS25] {message}", flush=True)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def true_value(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def ensure_directories() -> None:
    for path in (
        GAME_DIR,
        CONFIG_DIR,
        DEDICATED_DIR,
        INSTALLER_DIR,
        DLC_DIR,
        PDLC_DIR,
        LOG_DIR,
        DESKTOP_DIR,
        HOME / ".vnc",
    ):
        path.mkdir(parents=True, exist_ok=True)


def run_checked(args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    log("Ausführen: " + " ".join(args))
    return subprocess.run(args, text=True, timeout=timeout, check=True)


def prefix_files_exist(prefix: pathlib.Path = PREFIX) -> bool:
    """Check prefix state without assuming distro-provided DLL locations."""
    return (
        (prefix / "system.reg").stat().st_size > 0
        and (prefix / "user.reg").stat().st_size > 0
        and (prefix / "drive_c/windows/system32").is_dir()
    )


def prefix_runs() -> bool:
    try:
        files_exist = prefix_files_exist()
    except OSError:
        files_exist = False
    if not files_exist:
        return False
    try:
        result = subprocess.run(
            ["wine", "cmd", "/d", "/s", "/c", "ver"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=int(env("WINECHECK_TIMEOUT", "45")),
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def wait_for_prefix(seconds: int = 60) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if prefix_runs():
            return True
        time.sleep(2)
    return False


def move_prefix_aside(label: str) -> pathlib.Path | None:
    if not PREFIX.exists():
        return None
    subprocess.run(["wineserver", "-k"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    destination = PREFIX.with_name(f"{PREFIX.name}.{label}-{timestamp}")
    counter = 1
    while destination.exists():
        destination = PREFIX.with_name(f"{PREFIX.name}.{label}-{timestamp}-{counter}")
        counter += 1
    PREFIX.rename(destination)
    return destination


def wineboot(mode: str, timeout: int, attempt: int) -> int:
    boot_env = os.environ.copy()
    boot_env["WINEDEBUG"] = "err+all,warn+all"
    return run_logged(
        ["wineboot", mode],
        LOG_DIR / f"wineboot-{attempt}.log",
        timeout,
        process_env=boot_env,
        progress_interval=15,
    )


def ensure_prefix() -> None:
    ensure_directories()
    if wait_for_prefix(6):
        log("Wine-Prefix ist vollständig und ausführbar.")
        return

    timeout = int(env("WINEBOOT_TIMEOUT", "180"))
    try:
        layout_exists = prefix_files_exist()
    except OSError:
        layout_exists = False

    if layout_exists:
        log("Vorhandener Wine-Prefix wird für Wine 11 aktualisiert.")
        status = wineboot("--update", timeout, 0)
        if status == 0 and wait_for_prefix(60):
            log("Vorhandener Wine-Prefix wurde erfolgreich aktualisiert.")
            return
        log(f"Aktualisierung des vorhandenen Prefix fehlgeschlagen (Status {status}).")

    # Older image revisions expected built-in Wine DLLs inside drive_c and
    # could therefore move a healthy prefix aside. Prefer restoring the newest
    # usable candidate so activation data is retained.
    candidates = sorted(HOME.glob(f"{PREFIX.name}.broken-*"), reverse=True)
    for candidate in candidates:
        try:
            usable_layout = prefix_files_exist(candidate)
        except OSError:
            usable_layout = False
        if not usable_layout:
            continue
        displaced = move_prefix_aside("failed-current")
        candidate.rename(PREFIX)
        log(f"Vorheriger Wine-Prefix wurde aus {candidate} wiederhergestellt.")
        status = wineboot("--update", timeout, 0)
        if status == 0 and wait_for_prefix(60):
            log("Wiederhergestellter Wine-Prefix ist ausführbar.")
            return
        failed = move_prefix_aside("failed-recovery")
        log(f"Wiederherstellung war nicht ausführbar; Prefix liegt unter {failed}.")
        if displaced and displaced.exists():
            displaced.rename(PREFIX)

    if PREFIX.exists():
        backup = move_prefix_aside("broken")
        log(f"Unvollständiger Wine-Prefix wurde nach {backup} verschoben.")

    for attempt in (1, 2):
        PREFIX.mkdir(parents=True, exist_ok=True)
        log(f"Wine-Prefix wird neu erzeugt (Versuch {attempt}/2, Timeout {timeout}s).")
        status = wineboot("--init", timeout, attempt)
        if status == 0 and wait_for_prefix(60):
            log("Wine-Prefix wurde erfolgreich verifiziert.")
            return
        failed = move_prefix_aside(f"failed-init-{attempt}")
        log(
            f"Wine-Prefix-Versuch {attempt}/2 endete mit Status {status}; "
            f"siehe {LOG_DIR / f'wineboot-{attempt}.log'}. Daten liegen unter {failed}."
        )

    raise RuntimeError("Wine-Prefix konnte nach zwei Versuchen nicht funktionsfähig angelegt werden")


def configure_headless_wine() -> None:
    if env("WINE_AUDIO_MODE", "disabled").lower() != "disabled":
        log(f"Wine-Audio bleibt aktiviert ({env('WINE_AUDIO_MODE')}).")
        return
    marker = PREFIX / ".fs25-headless-audio-disabled"
    if marker.exists():
        return
    overrides = env("WINEDLLOVERRIDES", "mscoree=d")
    os.environ["WINEDLLOVERRIDES"] = overrides + ";winealsa.drv=d;winepulse.drv=d;winedbg.exe=d"
    try:
        run_checked(
            ["wine", "reg", "add", r"HKCU\Software\Wine\Drivers", "/v", "Audio", "/t", "REG_SZ", "/d", "disabled", "/f"],
            timeout=60,
        )
        marker.touch()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        log("Wine-Audio konnte nicht dauerhaft deaktiviert werden; Start wird fortgesetzt.")


def link_persistent(source: pathlib.Path, target: pathlib.Path) -> None:
    source.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() and target.resolve() == source.resolve():
        return
    if target.exists() and target.is_dir() and not target.is_symlink():
        shutil.copytree(target, source, dirs_exist_ok=True)
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.exists():
        shutil.rmtree(target)
    target.symlink_to(source, target_is_directory=True)


def atomic_xml(path: pathlib.Path, root: ET.Element) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="    ")
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        temp = pathlib.Path(handle.name)
        ET.ElementTree(root).write(handle, encoding="utf-8", xml_declaration=True)
    ET.parse(temp)
    os.replace(temp, path)


def validated_port(name: str, default: int) -> str:
    raw = env(name, str(default))
    try:
        number = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} muss eine Zahl sein: {raw}") from exc
    if number < 1024 or number > 65535:
        raise RuntimeError(f"{name} muss zwischen 1024 und 65535 liegen: {number}")
    return str(number)


def load_or_create(path: pathlib.Path, root_name: str) -> ET.Element:
    if path.is_file():
        try:
            root = ET.parse(path).getroot()
            if root.tag == root_name:
                return root
        except (ET.ParseError, OSError):
            pass
    return ET.Element(root_name)


def child(parent: ET.Element, name: str, attributes: dict[str, str] | None = None) -> ET.Element:
    found = parent.find(name)
    if found is None:
        found = ET.SubElement(parent, name, attributes or {})
    elif attributes:
        found.attrib.update(attributes)
    return found


def configure() -> None:
    ensure_directories()
    web_port = validated_port("WEB_PORT", 7999)
    game_port = validated_port("SERVER_PORT", 10823)
    if web_port == game_port:
        raise RuntimeError("WEB_PORT und SERVER_PORT müssen verschieden sein")

    server_path = GAME_DIR / "dedicatedServer.xml"
    server = load_or_create(server_path, "server")
    web = child(server, "webserver", {"port": web_port})
    admin = child(web, "initial_admin")
    child(admin, "username").text = env("WEB_USERNAME", "admin")
    child(admin, "passphrase").text = env("WEB_PASSWORD", "webpassword")
    child(
        server,
        "game",
        {
            "description": "Farming Simulator 25",
            "name": "FarmingSimulator2025",
            "exe": "FarmingSimulator2025Game.exe",
        },
    )
    atomic_xml(server_path, server)

    config_path = DEDICATED_DIR / "dedicatedServerConfig.xml"
    gameserver = load_or_create(config_path, "gameserver")
    settings = child(gameserver, "settings")
    requested_map = env("SERVER_MAP").strip()
    existing_map = (settings.findtext("mapID") or "").strip()
    existing_filename = (settings.findtext("mapFilename") or "").strip()
    values = {
        "game_name": env("SERVER_NAME", "FS25 Server"),
        "admin_password": env("SERVER_ADMIN", "adminpassword"),
        "game_password": env("SERVER_PASSWORD"),
        "savegame_index": env("SAVEGAME_INDEX", "1"),
        "max_player": env("SERVER_PLAYERS", "16"),
        "port": game_port,
        "language": env("SERVER_REGION", "de"),
        "auto_save_interval": env("SERVER_SAVE_INTERVAL", "180.000000"),
        "stats_interval": env("SERVER_STATS_INTERVAL", "31536000"),
        "crossplay_allowed": env("SERVER_CROSSPLAY", "true"),
        "pause_game_if_empty": env("SERVER_PAUSE", "2"),
        "mapID": requested_map or existing_map or "MapUS",
        "mapFilename": "default" if requested_map else (existing_filename or "default"),
    }
    for key, value in values.items():
        child(settings, key).text = value
    atomic_xml(config_path, gameserver)
    log(f"Konfiguration geschrieben: web={web_port} game={game_port} map={values['mapID']}")


def write_desktop_file(name: str, title: str, command: str, icon: str) -> None:
    path = DESKTOP_DIR / name
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={title}\n"
        f"Exec=xfce4-terminal --hold --command=\"{command}\"\n"
        "Terminal=false\n"
        f"Icon={icon}\n"
    )
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def create_desktop_shortcuts() -> None:
    ensure_directories()
    write_desktop_file("fs25-install.desktop", "FS25 installieren / aktivieren", "/opt/fs25/fs25ctl.py install", "system-software-install")
    write_desktop_file("fs25-server.desktop", "FS25 Webserver starten", "/opt/fs25/fs25ctl.py start-webserver", "applications-games")
    write_desktop_file("fs25-dlcs.desktop", "FS25 DLCs installieren", "/opt/fs25/fs25ctl.py install-dlcs", "system-software-install")
    path = DESKTOP_DIR / "fs25-web.desktop"
    path.write_text(
        "[Desktop Entry]\nType=Application\nName=GIANTS Webinterface öffnen\n"
        f"Exec=firefox-esr http://127.0.0.1:{validated_port('WEB_PORT', 7999)}/\n"
        "Terminal=false\nIcon=web-browser\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def prepare() -> None:
    ensure_prefix()
    configure_headless_wine()
    link_persistent(GAME_DIR, WINE_GAME_DIR)
    link_persistent(CONFIG_DIR, WINE_CONFIG_DIR)
    create_desktop_shortcuts()
    configure()


def archive_command(archive: pathlib.Path, output: pathlib.Path) -> list[str]:
    output.mkdir(parents=True, exist_ok=True)
    for executable in ("7z", "7zz", "7za"):
        path = shutil.which(executable)
        if path:
            return [path, "x", "-y", f"-o{output}", str(archive)]
    bsdtar = shutil.which("bsdtar")
    if bsdtar:
        return [bsdtar, "-xf", str(archive), "-C", str(output)]
    raise RuntimeError("Kein Archivprogramm vorhanden (7z/7zz/7za/bsdtar)")


def find_installer() -> pathlib.Path | None:
    names = {"setup.exe", "farmingsimulator2025.exe"}
    candidates = sorted(
        path for path in INSTALLER_DIR.rglob("*")
        if path.is_file() and path.name.lower() in names
    )
    return candidates[0] if candidates else None


def run_logged(
    args: list[str],
    log_path: pathlib.Path,
    timeout: int,
    cwd: pathlib.Path | None = None,
    progress_interval: int = 30,
    process_env: dict[str, str] | None = None,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log("Ausführen: " + " ".join(args))
    with log_path.open("w", encoding="utf-8", errors="replace") as output:
        process = subprocess.Popen(
            args,
            cwd=cwd,
            env=process_env,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        started = time.monotonic()
        while process.poll() is None:
            elapsed = int(time.monotonic() - started)
            if elapsed >= timeout:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                return 124
            try:
                process.wait(timeout=min(progress_interval, timeout - elapsed))
            except subprocess.TimeoutExpired:
                log(f"Prozess läuft seit {int(time.monotonic() - started)}s; Log: {log_path}")
        return process.returncode


def create_slice_aliases(installer: pathlib.Path) -> None:
    stem = installer.stem
    if stem.lower() == "setup":
        stem = "Setup"
    elif stem.lower() == "farmingsimulator2025":
        stem = "FarmingSimulator2025"
    count = 0
    for item in installer.parent.iterdir():
        match = re.match(r"^[^_]+_([0-9]+[A-Za-z])\.[Bb][Ii][Nn]$", item.name)
        if not item.is_file() or not match:
            continue
        alias = installer.parent / f"{stem}-{match.group(1).lower()}.bin"
        if not alias.exists():
            try:
                os.link(item, alias)
            except OSError:
                alias.symlink_to(item.name)
        count += 1
    if count:
        log(f"{count} Installer-Slices sind unter den erwarteten Namen verfügbar.")


def install() -> None:
    prepare()
    required_gib = int(env("REQUIRED_SPACE_GB", "50"))
    available_gib = shutil.disk_usage(HOME).free // (1024 ** 3)
    if not (GAME_EXE.is_file() and SERVER_EXE.is_file()) and available_gib < required_gib:
        raise RuntimeError(
            f"Nicht genug freier Speicher: {required_gib} GiB benötigt, {available_gib} GiB verfügbar"
        )
    installer = find_installer()
    if not (GAME_EXE.is_file() and SERVER_EXE.is_file()) and installer is None:
        archives = sorted(
            path for path in INSTALLER_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in {".img", ".iso", ".zip"}
        )
        if archives:
            extracted = INSTALLER_DIR / "extracted"
            if extracted.exists():
                shutil.rmtree(extracted)
            log(f"Entpacke {archives[0].name} ...")
            run_checked(archive_command(archives[0], extracted))
            installer = find_installer()

    if not (GAME_EXE.is_file() and SERVER_EXE.is_file()):
        if installer is None:
            raise RuntimeError(f"Kein Setup in {INSTALLER_DIR} gefunden")
        create_slice_aliases(installer)
        args = ["wine", str(installer)]
        if env("INSTALL_MODE", "silent") == "silent":
            args.extend(["/SILENT", "/NOCANCEL", "/NOICONS"])
        status = run_logged(
            args,
            LOG_DIR / "fs25-installer.log",
            int(env("INSTALL_TIMEOUT", "7200")),
            installer.parent,
            int(env("INSTALL_PROGRESS_INTERVAL", "30")),
        )
        if status != 0:
            raise RuntimeError(f"FS25-Installer endete mit Status {status}")

    if not (GAME_EXE.is_file() and SERVER_EXE.is_file()):
        raise RuntimeError("Installation ist unvollständig: Spiel- oder Serverprogramm fehlt")
    log("Installation verifiziert.")

    if true_value(env("ACTIVATE_AFTER_INSTALL", "true")):
        status = run_logged(
            ["wine", str(GAME_EXE)],
            LOG_DIR / "fs25-activation.log",
            int(env("ACTIVATION_TIMEOUT", "7200")),
            GAME_DIR,
        )
        if status not in {0, 124}:
            raise RuntimeError(f"Aktivierung endete mit Status {status}")
        if status == 124:
            log("Aktivierungszeitraum ist abgelaufen; der Prozess wurde beendet.")

    configure()
    if true_value(env("AUTO_INSTALL_DLC", "false")):
        install_dlcs()
    log("Einrichtung abgeschlossen.")


def dlc_name(path: pathlib.Path) -> str:
    raw = path.stem
    prefix = "FarmingSimulator25_"
    if raw.lower().startswith(prefix.lower()):
        raw = raw[len(prefix):]
    return raw.split("_", 1)[0]


def install_dlcs() -> None:
    prepare()
    extracted_root = DLC_DIR / ".extracted"
    extracted_root.mkdir(parents=True, exist_ok=True)
    for archive in sorted(DLC_DIR.iterdir()):
        if not archive.is_file() or archive.suffix.lower() not in {".img", ".iso", ".zip"}:
            continue
        target = extracted_root / archive.stem
        if not target.exists():
            log(f"Entpacke DLC-Archiv {archive.name} ...")
            run_checked(archive_command(archive, target))

    installers = sorted(
        {path.resolve() for root in (DLC_DIR, extracted_root) for path in root.rglob("*.exe") if path.is_file()},
        key=lambda path: path.name.lower(),
    )
    if not installers:
        log(f"Keine DLC-Installer in {DLC_DIR} gefunden.")
        return

    failures = 0
    log(f"Verarbeite {len(installers)} DLC-Installer nacheinander.")
    for installer in installers:
        name = dlc_name(installer)
        if (PDLC_DIR / f"{name}.dlc").is_file():
            log(f"{name} ist bereits installiert; überspringe {installer.name}.")
            continue
        status = run_logged(
            ["wine", str(installer)],
            LOG_DIR / f"dlc-{name}.log",
            int(env("DLC_INSTALL_TIMEOUT", "7200")),
            installer.parent,
        )
        if status != 0:
            failures += 1
            log(f"DLC {name} endete mit Status {status}.")
    if failures:
        raise RuntimeError(f"{failures} DLC-Installation(en) sind fehlgeschlagen")
    log("Alle gefundenen DLC-Installer wurden verarbeitet.")


WEB_PATCH_BEGIN = "/* === FS25 PELICAN HOST PATCH BEGIN === */"
WEB_PATCH_END = "/* === FS25 PELICAN HOST PATCH END === */"


def patch_web() -> None:
    frontend = GAME_DIR / "web_data" / "js" / "frontend.js"
    if frontend.is_file():
        content = frontend.read_text(encoding="utf-8", errors="replace")
        content = re.sub(
            re.escape(WEB_PATCH_BEGIN) + r".*?" + re.escape(WEB_PATCH_END),
            "",
            content,
            flags=re.DOTALL,
        ).rstrip()
        patch = r'''
/* === FS25 PELICAN HOST PATCH BEGIN === */
(function () {
  if (window.__fs25PelicanHostPatch) return;
  window.__fs25PelicanHostPatch = true;
  function internal(host) {
    return host === "localhost" || host === "127.0.0.1" ||
      /^10\./.test(host) || /^192\.168\./.test(host) ||
      /^172\.(1[6-9]|2[0-9]|3[01])\./.test(host);
  }
  function rewrite() {
    document.querySelectorAll("a[href]").forEach(function (node) {
      try {
        var url = new URL(node.href, window.location.href);
        if (internal(url.hostname)) {
          url.hostname = window.location.hostname;
          url.port = window.location.port;
          node.href = url.toString();
        }
      } catch (_) {}
    });
  }
  new MutationObserver(rewrite).observe(document.documentElement, {childList:true, subtree:true});
  rewrite();
})();
/* === FS25 PELICAN HOST PATCH END === */
'''
        frontend.write_text(content + "\n" + patch, encoding="utf-8")
        log("Webinterface-Hostkorrektur ist aktiv.")

    imports = {
        GAME_DIR / "web_data/css/grid.css": 'https://cdn.jsdelivr.net/gh/yellowfromseegg/FS25-Webinterface-DarkMode@main/dark-theme-grid.css',
        GAME_DIR / "web_data/css/main.css": 'https://cdn.jsdelivr.net/gh/yellowfromseegg/FS25-Webinterface-DarkMode@main/dark-theme-main.css',
    }
    begin = "/* WEB_DARKMODE_BEGIN */"
    end = "/* WEB_DARKMODE_END */"
    enabled = true_value(env("WEB_DARKMODE", "false"))
    for path, url in imports.items():
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        content = re.sub(re.escape(begin) + r".*?" + re.escape(end) + r"\s*", "", content, flags=re.DOTALL)
        if enabled:
            content = f'{begin}\n@import url("{url}");\n{end}\n' + content
        path.write_text(content, encoding="utf-8")


def start_webserver() -> None:
    prepare()
    if not SERVER_EXE.is_file():
        raise RuntimeError("dedicatedServer.exe fehlt; FS25 muss zuerst installiert werden")
    patch_web()
    os.chdir(GAME_DIR)
    os.execvp("wine", ["wine", str(SERVER_EXE)])


def autostart_game() -> None:
    port = int(validated_port("WEB_PORT", 7999))
    hosts = ["127.0.0.1"]
    try:
        import socket
        hosts.append(socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass
    base = ""
    for _ in range(60):
        for host in hosts:
            candidate = f"http://{host}:{port}/index.html?lang=en"
            try:
                with urllib.request.urlopen(candidate, timeout=2) as response:
                    if response.status < 400:
                        base = candidate
                        break
            except Exception:
                continue
        if base:
            break
        time.sleep(2)
    if not base:
        raise RuntimeError("GIANTS-Webinterface wurde nicht rechtzeitig erreichbar")

    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    login_data = urllib.parse.urlencode(
        {"username": env("WEB_USERNAME", "admin"), "password": env("WEB_PASSWORD", "webpassword"), "login": "Login"}
    ).encode()
    with opener.open(base, login_data, timeout=15) as response:
        response.read()
    with opener.open(base, timeout=15) as response:
        html = response.read().decode("utf-8", errors="replace")

    expected = (
        "game_name", "admin_password", "game_password", "savegame", "server_port",
        "max_player", "mp_language", "auto_save_interval", "stats_interval", "pause_game_if_empty",
    )
    params: dict[str, str] = {}
    for name, value in re.findall(r'<input[^>]+name="([^"]+)"[^>]+value="([^"]*)"', html, re.I):
        if name in expected:
            params[name] = value
    for name in expected:
        if name not in params:
            select = re.search(rf'<select[^>]+name="{re.escape(name)}".*?<option[^>]+value="([^"]*)"[^>]*selected', html, re.I | re.S)
            if select:
                params[name] = select.group(1)
    missing = [name for name in expected if name not in params]
    if missing:
        raise RuntimeError("Startformular ist unvollständig: " + ", ".join(missing))
    if re.search(r'name="crossplay_allowed"[^>]+checked', html, re.I):
        params["crossplay_allowed"] = "on"
    params["start_server"] = "Start"
    with opener.open(base, urllib.parse.urlencode(params).encode(), timeout=30) as response:
        response.read()
    log("Spielserver wurde über das GIANTS-Webinterface gestartet.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("prepare", "configure", "install", "install-dlcs", "patch-web", "start-webserver", "autostart-game"),
    )
    args = parser.parse_args()
    try:
        {
            "prepare": prepare,
            "configure": configure,
            "install": install,
            "install-dlcs": install_dlcs,
            "patch-web": patch_web,
            "start-webserver": start_webserver,
            "autostart-game": autostart_game,
        }[args.command]()
        return 0
    except Exception as exc:
        log(f"FEHLER: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
