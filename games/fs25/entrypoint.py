#!/usr/bin/env python3
"""Pelican entrypoint for the Farming Simulator 25 image."""

from __future__ import annotations

import os
import pathlib
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time


HOME = pathlib.Path("/home/container")
LOG_DIR = HOME / "logs"
GAME_DIR = HOME / "game" / "Farming Simulator 2025"
SERVER_EXE = GAME_DIR / "dedicatedServer.exe"
CONTROL = "/opt/fs25/fs25ctl.py"
children: list[subprocess.Popen] = []
stopping = False


def log(message: str) -> None:
    print(f"[FS25] {message}", flush=True)


def spawn(args: list[str], log_name: str | None = None) -> subprocess.Popen:
    target = None
    if log_name:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        target = (LOG_DIR / log_name).open("a", encoding="utf-8", errors="replace")
    process = subprocess.Popen(args, stdout=target, stderr=subprocess.STDOUT, start_new_session=True)
    children.append(process)
    return process


def stop_children(signum: int = signal.SIGTERM) -> None:
    global stopping
    if stopping:
        return
    stopping = True
    for process in reversed(children):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signum)
            except ProcessLookupError:
                pass
    deadline = time.time() + 15
    for process in reversed(children):
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.1, deadline - time.time()))
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


def signal_handler(signum: int, _frame) -> None:
    stop_children(signum)
    raise SystemExit(128 + signum)


def find_novnc_webroot() -> str:
    for candidate in ("/usr/share/novnc", "/usr/share/webapps/novnc"):
        if pathlib.Path(candidate).is_dir():
            return candidate
    raise RuntimeError("noVNC-Webverzeichnis wurde nicht gefunden")


def start_xvnc() -> subprocess.Popen:
    pathlib.Path("/tmp/.X0-lock").unlink(missing_ok=True)
    pathlib.Path("/tmp/.X11-unix/X0").unlink(missing_ok=True)
    vnc_dir = HOME / ".vnc"
    vnc_dir.mkdir(parents=True, exist_ok=True)
    vnc_dir.chmod(0o700)
    geometry = os.environ.get("VNC_GEOMETRY", "1280x720")
    command = ["Xvnc", ":0", "-depth", "24", "-geometry", geometry, "-rfbport", "5900"]
    password = os.environ.get("VNC_PASSWORD", "")
    if len(password) >= 6:
        result = subprocess.run(
            ["vncpasswd", "-f"],
            input=(password + "\n").encode(),
            capture_output=True,
            check=True,
        )
        passwd = vnc_dir / "passwd"
        passwd.write_bytes(result.stdout)
        passwd.chmod(0o600)
        command.append(f"-PasswordFile={passwd}")
    else:
        command.append("-SecurityTypes=None")
    process = spawn(command, "xvnc.log")
    for _ in range(30):
        if process.poll() is not None:
            raise RuntimeError("Xvnc wurde vorzeitig beendet; siehe logs/xvnc.log")
        if subprocess.run(["xdpyinfo"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return process
        time.sleep(1)
    raise RuntimeError("Xvnc wurde nicht rechtzeitig bereit")


def start_desktop() -> None:
    runtime = pathlib.Path(os.environ["XDG_RUNTIME_DIR"])
    runtime.mkdir(parents=True, exist_ok=True)
    runtime.chmod(0o700)
    sessions = HOME / ".cache" / "sessions"
    if sessions.exists():
        shutil.rmtree(sessions)
    config = HOME / ".config"
    config.mkdir(parents=True, exist_ok=True)
    (config / "user-dirs.dirs").write_text(f'XDG_DESKTOP_DIR="{HOME / "Desktop"}"\n', encoding="utf-8")

    dbus = subprocess.run(
        ["dbus-daemon", "--session", "--fork", "--print-address=1", "--print-pid=1"],
        text=True,
        capture_output=True,
        check=True,
    )
    lines = [line.strip() for line in dbus.stdout.splitlines() if line.strip()]
    if lines:
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = lines[0]
    spawn(["startxfce4"], "xfce.log")
    time.sleep(4)
    fallbacks = (
        ("xfsettingsd", ["xfsettingsd"]),
        ("xfwm4", ["xfwm4", "--replace", "--compositor=off"]),
        ("xfdesktop", ["xfdesktop"]),
        ("xfce4-panel", ["xfce4-panel"]),
    )
    for name, command in fallbacks:
        running = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", name], stdout=subprocess.DEVNULL).returncode == 0
        if not running:
            spawn(command, "xfce.log")


def startup_command() -> list[str]:
    startup = os.environ.get("STARTUP", 'wine "/home/container/game/Farming Simulator 2025/dedicatedServer.exe"')
    startup = re.sub(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}", lambda match: os.environ.get(match.group(1), ""), startup)
    startup = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda match: os.environ.get(match.group(1), ""), startup)
    command = shlex.split(startup)
    if not command:
        raise RuntimeError("STARTUP ist leer")
    return command


def main() -> int:
    os.environ.update(
        {
            "HOME": str(HOME),
            "USER": "container",
            "LOGNAME": "container",
            "WINEPREFIX": str(HOME / ".fs25server"),
            "WINEARCH": "win64",
            "WINEDEBUG": os.environ.get("WINEDEBUG", "-all"),
            "DISPLAY": ":0",
            "XDG_RUNTIME_DIR": "/tmp/xdg-runtime-fs25",
        }
    )
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal_handler)

    xvnc = start_xvnc()
    novnc_port = os.environ.get("NOVNC_PORT", "6080")
    spawn(["websockify", "--web", find_novnc_webroot(), novnc_port, "localhost:5900"], "novnc.log")
    start_desktop()
    subprocess.run([CONTROL, "prepare"], check=True)

    public_host = os.environ.get("PUBLIC_IP") or os.environ.get("SERVER_IP") or "SERVER-IP"
    log(f"noVNC: http://{public_host}:{novnc_port}/vnc.html?resize=remote&autoconnect=1")
    log(f"GIANTS-Webinterface: http://{public_host}:{os.environ.get('WEB_PORT', '7999')}")
    log(f"Spielport: {os.environ.get('SERVER_PORT', '10823')}/tcp+udp")
    log("FS25 image ready.")

    if not SERVER_EXE.is_file():
        log("Noch keine Installation erkannt. Installer nach /home/container/installer hochladen.")
        if os.environ.get("AUTO_INSTALL", "false").lower() == "true":
            spawn([CONTROL, "install"], "automatic-install.log")
        return xvnc.wait()

    if os.environ.get("AUTO_INSTALL_DLC", "false").lower() == "true":
        subprocess.run([CONTROL, "install-dlcs"], check=True)

    mode = os.environ.get("AUTOSTART_SERVER", "web_only").lower()
    if mode == "false":
        log("Installation erkannt. Webserver kann über den Desktop gestartet werden.")
        return xvnc.wait()
    if mode not in {"true", "web_only"}:
        raise RuntimeError(f"Ungültiger AUTOSTART_SERVER-Wert: {mode}")

    subprocess.run([CONTROL, "configure"], check=True)
    subprocess.run([CONTROL, "patch-web"], check=True)
    command = startup_command()
    log("Startbefehl: " + " ".join(command))
    server = spawn(command, "dedicated-server.log")
    if mode == "true":
        spawn([CONTROL, "autostart-game"], "autostart-game.log")
    return server.wait()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"FEHLER: {exc}")
        stop_children()
        raise SystemExit(1)
    finally:
        stop_children()
