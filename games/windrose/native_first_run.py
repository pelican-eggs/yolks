"""Windrose Linux first-start orchestration for the 0.10.0.9.32 publisher build."""

import fcntl
import json
import math
import os
import secrets
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from patch_native_world_backup import PRESETS, WORLD_MEMBER, patch_backup, validated_members

GAME = "/usr/local/bin/windrose-pelican"
SERVER = Path("R5/ServerDescription.json")
SAVES = Path("R5/Saved/SaveProfiles/Default")
RUNTIME = SAVES / "RocksDB_v2"
BACKUPS = SAVES / "RocksDB_v2_Backups/Worlds"
GAME_LOG = Path("R5/Saved/Logs/R5.log")
STATE = Path(".windrose-first-run")
KEY = "ServerDescription_Persistent"
READY = b"LogGlobalStatus: LoadMap Load map complete /Game/Maps/GYM/Genlandia/GenlandiaMulty"
EXIT = b"LogExit: Exiting."
active = None
interrupted = False


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path, value):
    stage = path.with_name(f".{path.name}.{secrets.token_hex(6)}")
    try:
        with stage.open("x", encoding="utf-8") as out:
            os.fchmod(out.fileno(), 0o600)
            json.dump(value, out, ensure_ascii=False, allow_nan=False, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(stage, path)
        sync_directory(path.parent)
    finally:
        stage.unlink(missing_ok=True)


def json_file(path):
    if path.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f"Invalid JSON input: {path.name}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def start_signal(signum, _frame):
    global interrupted
    interrupted = True


def stop_game(process):
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
    return process.wait(timeout=25)


def restore_access(original, temporary):
    current = json_file(SERVER)
    config = current[KEY]
    if any(config.get(key) not in (temporary[key], value) for key, value in original.items()):
        raise ValueError("Access settings changed during first launch.")
    config.update(original)
    write_json(SERVER, current)


def validate_archive(path, world_id, test_crc=False):
    with ZipFile(path) as z:
        validated_members(z)
        result = json.loads(z.read(WORLD_MEMBER))["WorldDescription"]
        if result["islandId"] != world_id or (test_crc and z.testzip() is not None):
            raise ValueError("Invalid or unrelated first-world backup.")
        return result


def console_tail(path):
    try:
        with path.open("rb") as stream:
            size = os.fstat(stream.fileno()).st_size
            stream.seek(max(0, size - 4 * 1024 * 1024))
            return stream.read(4 * 1024 * 1024)
    except FileNotFoundError:
        return b""


def wait_for_snapshot(game, console, snapshot):
    deadline = time.monotonic() + 180
    ready = False
    while game.poll() is None and not interrupted and time.monotonic() < deadline:
        ready = ready or READY in console_tail(console) or READY in console_tail(GAME_LOG)
        candidates = list(BACKUPS.glob("*/*_0.10.0_Latest.zip"))
        if ready and len(candidates) == 1:
            source = candidates[0]
            world_id = source.parent.name
            if (len(world_id) == 32 and all(c in "0123456789abcdefABCDEF" for c in world_id)
                    and source.name == f"{world_id}_0.10.0_Latest.zip"
                    and source.is_file() and not source.is_symlink() and source.stat().st_size <= 2 * 1024**3):
                target = snapshot / source.name
                try:
                    shutil.copyfile(source, target)
                    validate_archive(target, world_id, test_crc=True)
                except (BadZipFile, FileNotFoundError):
                    target.unlink(missing_ok=True)
                else:
                    with target.open("rb") as data:
                        os.fsync(data.fileno())
                    sync_directory(snapshot)
                    return world_id, source, target
        time.sleep(1)
    raise ValueError(f"No verified natural backup arrived during the first launch (gameplay={ready}, canonical={len(list(BACKUPS.glob('*/*_0.10.0_Latest.zip')))}).")


def checked_move(source, destination):
    if source.is_symlink() or destination.exists() or destination.is_symlink():
        raise ValueError("Unsafe or occupied first-world move.")
    os.rename(source, destination)
    sync_directory(source.parent)
    sync_directory(destination.parent)


def cold_restore(game_config, world_id, archive):
    worlds = list(RUNTIME.glob("*/Worlds/*/WorldDescription.json"))
    if worlds != [RUNTIME / "0.10.0/Worlds" / world_id / "WorldDescription.json"]:
        raise ValueError("Fresh runtime directory does not contain exactly the selected world.")
    patched = STATE / "patched.zip"
    patch_backup(archive, patched, world_id, game_config["name"], game_config["preset"])
    expected = validate_archive(patched, world_id, test_crc=True)
    # Keep both originals. The game's restore path creates a new live RocksDB tree.
    checked_move(game_config["latest"], STATE / "previous-latest.zip")
    checked_move(RUNTIME, STATE / "previous-runtime")
    checked_move(patched, game_config["latest"])
    return expected


def same_values(a, b):
    if type(a) is bool or type(b) is bool:
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_values(a[key], b[key]) for key in a)
    return a == b


def startup_lines(stream):
    pending = bytearray()
    with selectors.DefaultSelector() as poller:
        poller.register(stream, selectors.EVENT_READ)
        while True:
            if not poller.select(timeout=1.0):
                yield None
                continue
            chunk = os.read(stream.fileno(), 65536)
            if not chunk:
                if pending:
                    yield bytes(pending)
                return
            pending.extend(chunk)
            while (index := pending.find(b"\n")) >= 0:
                yield bytes(pending[:index + 1])
                del pending[:index + 1]
            if len(pending) > 1024 * 1024:
                raise ValueError("Unexpected oversized console line during world setup.")


def reopen(world_id, expected):
    global active
    # Preserve the first boot's log so only the new process can supply readiness.
    if GAME_LOG.exists():
        checked_move(GAME_LOG, STATE / "first-game.log")
    active = subprocess.Popen([GAME], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    confirmed = False
    deadline = time.monotonic() + 180
    try:
        for line in startup_lines(active.stdout):
            if interrupted and confirmed:
                return stop_game(active)
            if not confirmed:
                if time.monotonic() >= deadline or interrupted:
                    raise ValueError("Restored world did not verify before startup stopped or timed out.")
                if line is None:
                    line = next((entry + b"\n" for entry in console_tail(GAME_LOG).splitlines()
                                 if READY in entry), None)
            if line is None:
                continue
            if not confirmed and READY in line:
                descriptor = RUNTIME / "0.10.0/Worlds" / world_id / "WorldDescription.json"
                actual = json_file(descriptor)["WorldDescription"]
                selected = json_file(SERVER)[KEY]["WorldIslandId"]
                exact = ("islandId", "CreationTime", "WorldName", "WorldPresetType")
                if selected != world_id or any(actual[key] != expected[key] for key in exact):
                    raise ValueError("The relaunched world did not load the requested identity and settings.")
                if not same_values(actual["WorldSettings"], expected["WorldSettings"]):
                    raise ValueError("The relaunched world's difficulty parameters did not match.")
                write_json(STATE / "complete.json", {"world_id": world_id})
                (STATE / "pending.json").unlink()
                sync_directory(STATE)
                confirmed = True
                print("Windrose first-world settings verified.", flush=True)
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
        code = active.wait()
        return code if confirmed else 1
    finally:
        if active.poll() is None:
            stop_game(active)


def bootstrap(name, preset, config):
    global active
    if not 1 <= len(name) <= 64 or not name.strip() or any(ord(c) < 32 for c in name) or preset not in PRESETS:
        raise ValueError("Set a valid world name and an Easy, Medium or Hard difficulty.")
    if any(SAVES.glob("*/**/WorldDescription.json")) or RUNTIME.exists() or BACKUPS.exists() or GAME_LOG.exists():
        raise ValueError("An existing save directory needs manual review.")
    if config[KEY].get("AutoLoadLatestBackupIfHasBroken") is not True:
        raise ValueError("Enable Recover From Latest Backup for first-world setup.")
    snapshot = STATE / "snapshot"
    snapshot.mkdir(mode=0o700)
    section = config[KEY]
    native_port = section["DirectConnectionServerPort"]
    temporary_port = native_port
    while temporary_port == native_port:
        temporary_port = 49152 + secrets.randbelow(16384)
    temporary = {
        "DirectConnectionServerPort": temporary_port,
        "IsPasswordProtected": True,
        "Password": secrets.token_hex(12),
        "InviteCode": secrets.token_hex(12),
    }
    original = {key: section[key] for key in temporary}
    # A restart during setup stays held rather than bypassing the requested settings.
    write_json(STATE / "pending.json", {"restore": original, "temporary": temporary})
    section.update(temporary)
    write_json(SERVER, config)
    console = STATE / "first-console.log"
    with console.open("xb") as out:
        os.fchmod(out.fileno(), 0o600)
        active = subprocess.Popen([GAME], stdout=out, stderr=subprocess.STDOUT)
        try:
            world_id, latest, archive = wait_for_snapshot(active, console, snapshot)
        finally:
            code = stop_game(active)
            restore_access(original, temporary)
    exit_logged = any(
        EXIT in content or b"LogLinux: FPlatformMisc::RequestExit" in content
        for content in (console_tail(console), console_tail(GAME_LOG))
    )
    accepted_signal_exit = code in (130, 139, -signal.SIGINT, -signal.SIGSEGV) and exit_logged
    if interrupted or (code != 0 and not accepted_signal_exit):
        raise ValueError(f"Unexpected first-launch exit (code={code}, requested_exit_logged={exit_logged}). The verified backup and runtime were preserved.")
    if json_file(SERVER)[KEY].get("WorldIslandId") != world_id:
        raise ValueError("The verified first snapshot does not match the selected world after stop.")
    print(f"Windrose first launch stopped after a validated snapshot (exit {code}).", flush=True)
    expected = cold_restore({"name": name, "preset": preset, "latest": latest}, world_id, archive)
    return reopen(world_id, expected)


def main():
    signal.signal(signal.SIGINT, start_signal)
    signal.signal(signal.SIGTERM, start_signal)
    STATE.mkdir(mode=0o700, exist_ok=True)
    if STATE.is_symlink() or STATE.stat().st_mode & 0o077:
        raise ValueError("First-run state directory must be private.")
    with (STATE / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (STATE / "pending.json").exists() and not (STATE / "complete.json").is_file():
            raise ValueError("A previous first-run attempt is pending. Review its preserved files.")
        name = os.environ.get("WORLD_NAME", "")
        preset = os.environ.get("WORLD_PRESET_TYPE", "")
        config = json_file(SERVER)
        if len(config[KEY]["Password"]) > 31:
            raise ValueError("Windrose passwords must be shorter than 32 characters.")
        if (name or preset) and not config[KEY].get("WorldIslandId"):
            return bootstrap(name, preset, config)
    os.execv(GAME, [GAME])


if __name__ == "__main__":
    try:
        result = main()
    except (OSError, ValueError, KeyError, BadZipFile, subprocess.TimeoutExpired) as exc:
        message = str(exc) if type(exc) is ValueError else type(exc).__name__
        print(f"Windrose first-run setup held: {message}", file=sys.stderr)
        raise SystemExit(1) from None
    raise SystemExit(result if result >= 0 else 128 - result)
