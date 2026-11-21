"""Paths and process helpers shared by installation and runtime."""

from contextlib import contextmanager, suppress
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import tempfile


ROOT = Path("/mnt/server")
GAME = ROOT / "game"
WORK = ROOT / "work"
PROFILE = ROOT / "profile"
PROTON = ROOT / ".proton"
SECRETS = ROOT / ".fs25-secrets"
MARKER = GAME / ".fs25-install.json"
DEFAULT_PROTON = "GE-Proton11-12"
RELEASE = re.compile(r"GE-Proton([0-9]+)-([0-9]+)\Z")
PANEL_PRIVATE = frozenset({
    "FS25_PRODUCT_KEY", "FS25_DOWNLOAD_URL", "FS25_DLC_PRODUCT_KEYS", "FS25_DLC_INSTALL_SOURCES",
})


class Failure(Exception):
    pass


def secret(name, *, trim=True, multiline=False):
    try:
        with os.fdopen(os.open(SECRETS / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK),
                       encoding="utf-8") as handle:
            mode = os.fstat(handle.fileno()).st_mode
            if not stat.S_ISREG(mode) or mode & 0o077:
                raise Failure(f"Use a regular file with mode 0600 for .fs25-secrets/{name}.")
            value = handle.read(8193)
    except FileNotFoundError:
        return ""
    if len(value) > 8192:
        raise Failure(f".fs25-secrets/{name} is too large.")
    value = value.strip() if trim else value.rstrip("\r\n")
    if any(ord(char) < 32 and not (multiline and char in "\n\r\t") for char in value):
        raise Failure(f".fs25-secrets/{name} contains an invalid control character.")
    return value


def panel_setting(variable, filename, *, multiline=False):
    value = os.environ.get(variable, "").strip()
    if not value:
        return secret(filename, multiline=True) if multiline else secret(filename)
    if len(value) > 8192 or any(ord(char) < 32 and not (multiline and char in "\n\r\t") for char in value):
        raise Failure(f"{variable} contains invalid characters or is too long.")
    return value


def product_key():
    return panel_setting("FS25_PRODUCT_KEY", "activation-key").replace(" ", "")


def version(value):
    if not isinstance(value, str) or not RELEASE.fullmatch(value):
        raise Failure("Use a GE-Proton release tag such as GE-Proton11-12.")
    return value


def compat(tag):
    return PROTON / "compatdata" / version(tag)


def proton(tag):
    return PROTON / "releases" / version(tag) / "proton"


def proton_env(tag):
    prefix = compat(tag)
    steam = ROOT / ".steam" / "steam"
    protonfixes = ROOT / ".config" / "protonfixes"
    for directory in (prefix, steam, protonfixes):
        directory.mkdir(parents=True, exist_ok=True)
    env = {name: value for name, value in os.environ.items() if name not in PANEL_PRIVATE}
    return dict(env, HOME=str(ROOT), XDG_CONFIG_HOME=str(protonfixes.parent),
                XDG_CACHE_HOME=str(ROOT / ".cache"), XDG_DATA_HOME=str(ROOT / ".local" / "share"),
                USER=os.environ.get("USER") or "container",
                STEAM_COMPAT_DATA_PATH=str(prefix), STEAM_COMPAT_CLIENT_INSTALL_PATH=str(steam),
                WINEDEBUG="-all")


def run_proton(tag, *args, env, **kwargs):
    return subprocess.Popen([str(proton(tag)), "runinprefix", *map(str, args)],
                            env=env, start_new_session=True, stdin=subprocess.DEVNULL, **kwargs)


def terminate(process, grace=3):
    if process.poll() is None:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(grace)
        except subprocess.TimeoutExpired:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def stop_wine(tag, env):
    release = proton(tag).parent / "files"
    for binary in (release / "bin" / "wineserver", release / "bin-wow64" / "wineserver"):
        if binary.is_file() and (compat(tag) / "pfx").is_dir():
            with suppress(OSError, subprocess.TimeoutExpired):
                subprocess.run([binary, "-k"], env=dict(env, WINEPREFIX=str(compat(tag) / "pfx")),
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=4)
            break


@contextmanager
def xvfb(screen="1024x768x24"):
    read_fd, write_fd = os.pipe()
    process = None
    try:
        process = subprocess.Popen(["Xvfb", "-displayfd", str(write_fd), "-screen", "0",
                                    screen, "-nolisten", "tcp"],
                                   pass_fds=(write_fd,), start_new_session=True,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        os.close(write_fd)
        write_fd = None
        if not select.select([read_fd], [], [], 10)[0]:
            raise Failure("Xvfb did not become ready.")
        display = os.read(read_fd, 32).strip()
        if not display.isdigit():
            raise Failure("Xvfb failed to start.")
        yield ":" + display.decode("ascii")
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        if process is not None:
            terminate(process)


@contextmanager
def atomic_file(path, mode="w", **kwargs):
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, mode, **kwargs) as out:
            yield out
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        with suppress(FileNotFoundError):
            os.unlink(temp)


def valid_game(path):
    return all((path / name).is_file() and (path / name).stat().st_size
               for name in ("dedicatedServer.exe", "dedicatedServer.xml", "FarmingSimulator2025.exe"))
