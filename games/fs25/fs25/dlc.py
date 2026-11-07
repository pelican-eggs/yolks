"""Prepare, install and verify GIANTS DLCs using the two stages of the AMP template."""

from contextlib import contextmanager
import fcntl
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import unquote, urlencode, urljoin, urlsplit
from uuid import uuid4

from common import (PROFILE, ROOT, WORK, Failure, atomic_file, compat, panel_setting, proton,
                    run_proton, stop_wine, terminate, xvfb)
from install import CHUNK, PORTAL, allowed, remote


ALIAS = re.compile(r"[a-z][a-z0-9_-]{0,47}\Z")
PACKAGE = re.compile(r"([a-f0-9]{64})(?:\.exe|\.img)\Z")
MIN_FREE = 512 * CHUNK


def parse_entries(keys_text, sources_text):
    keys, sources = {}, {}
    for raw in re.split(r"[;\r\n]", keys_text):
        if not raw.strip():
            continue
        name, sep, key = raw.partition("=")
        name, key = name.strip().lower(), "".join(key.split()).upper()
        if not sep or not ALIAS.fullmatch(name):
            raise Failure("DLC Product Keys: use NAME=KEY, separated by semicolons.")
        if name in keys:
            raise Failure(f"Duplicate DLC key name: {name}.")
        if not re.fullmatch(r"[A-Z0-9-]{10,80}", key):
            raise Failure(f"Invalid product key format for DLC {name}.")
        keys[name] = key
    for raw in re.split(r"[;\r\n]", sources_text):
        if not raw.strip():
            continue
        name, sep, source = raw.partition("=")
        name, source = name.strip().lower(), source.strip()
        if not sep or name not in keys or not source:
            raise Failure("DLC Installation Sources: each NAME=SOURCE needs a matching DLC key.")
        if name in sources:
            raise Failure(f"Duplicate DLC source name: {name}.")
        if any(ord(char) < 32 for char in source):
            raise Failure(f"Invalid source for DLC {name}.")
        sources[name] = source
    return keys, sources


def settings():
    keys, sources = parse_entries(
        panel_setting("FS25_DLC_PRODUCT_KEYS", "dlc-product-keys", multiline=True),
        panel_setting("FS25_DLC_INSTALL_SOURCES", "dlc-install-sources", multiline=True),
    )
    value = os.environ.get("FS25_DLC_INSTALLER_TIMEOUT", "").strip() or "1800"
    if not re.fullmatch(r"[0-9]{1,4}", value) or not 60 <= int(value) <= 7200:
        raise Failure("DLC Installer Timeout must be between 60 and 7200 seconds.")
    return keys, sources, int(value)


def fingerprint(keys, sources):
    return hashlib.sha256(json.dumps([keys, sources], sort_keys=True).encode()).hexdigest()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    try:
        if not path.is_file() or path.is_symlink():
            return {}
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_json(path, value):
    with atomic_file(path, encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


@contextmanager
def operation():
    work = WORK / "dlc"
    work.mkdir(parents=True, exist_ok=True)
    with (work / "operation.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Failure("Another DLC operation is already running.") from None
        yield work


def giants_host(host):
    return bool(host and (host == "giants-software.com" or host.endswith(".giants-software.com")))


def is_dlc_url(value):
    if not allowed(value, giants_host):
        return False
    url = urlsplit(value)
    name = unquote(url.path.rsplit("/", 1)[-1])
    match = re.fullmatch(r"FarmingSimulator(?:20)?25[_-](.+)\.(exe|img)", name, re.I)
    if not match or url.fragment:
        return False
    # Exclude the base disc and similarly named game patches from discovery.
    product = re.sub(r"(?i)esd|setup|windows|win64|update|patch", "", match[1])
    return bool(re.search(r"[a-z]", product, re.I))


class PortalLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    try:
                        value = urljoin(PORTAL, value)
                        if is_dlc_url(value):
                            self.links.add(value)
                    except ValueError:
                        continue


def portal_links(key):
    try:
        with remote(PORTAL, lambda host: host == "eshop.giants-software.com",
                    data=urlencode({"activationKey": key, "foobar": "DOWNLOAD"}).encode()) as reply:
            body = reply.read(4 * CHUNK + 1)
    except (OSError, ValueError):
        raise Failure("The GIANTS DLC download portal could not be reached.") from None
    if len(body) > 4 * CHUNK:
        raise Failure("The GIANTS portal returned an unexpectedly large page.")
    parser = PortalLinks()
    parser.feed(body.decode("utf-8", "replace"))
    if not parser.links:
        raise Failure("GIANTS returned no identifiable FS25 DLC installer. Specify a direct source for this key.")
    return sorted(parser.links)


def uploaded_file(inbox, source):
    relative = PurePosixPath(source.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or ":" in source:
        raise Failure("Uploaded DLC sources must be relative to the dlc-installers directory.")
    path = (inbox / relative).resolve()
    if not path.is_relative_to(inbox.resolve()) or not path.is_file():
        raise Failure("An uploaded DLC source is missing or outside dlc-installers.")
    return path


def package_type(path):
    size = path.stat().st_size
    with path.open("rb") as stream:
        header = stream.read(64)
        if header[:2] == b"MZ" and len(header) == 64:
            offset = int.from_bytes(header[60:64], "little")
            if 64 <= offset <= size - 4:
                stream.seek(offset)
                if stream.read(4) == b"PE\0\0":
                    return ".exe"
        stream.seek(32768)
        descriptors = stream.read(2048 * 48)
    if any(descriptors[i + 1:i + 6] in (b"CD001", b"NSR02", b"NSR03")
           for i in range(0, len(descriptors), 2048)):
        return ".img"
    raise Failure("A DLC source is not a Windows PE installer or an ISO9660/UDF image.")


def fetch(url, target, previous):
    if not allowed(url, giants_host) or urlsplit(url).fragment:
        raise Failure("A remote DLC source must be a direct HTTPS download from GIANTS.")
    identity = hashlib.sha256(url.encode()).hexdigest()
    headers = {}
    for name, key in (("If-None-Match", "etag"), ("If-Modified-Since", "last_modified")):
        if isinstance(previous.get(key), str) and previous[key]:
            headers[name] = previous[key]
    try:
        with remote(url, giants_host, referer=PORTAL, headers=headers) as reply, target.open("wb") as out:
            length = reply.headers.get("Content-Length", "")
            length = int(length) if length.isdigit() else 0
            if length and shutil.disk_usage(target.parent).free < length + MIN_FREE:
                raise Failure("Not enough free space for the DLC download.")
            size, deadline = 0, time.monotonic() + 7200
            while block := reply.read(CHUNK):
                if time.monotonic() >= deadline:
                    raise Failure("The DLC download exceeded two hours.")
                if shutil.disk_usage(target.parent).free < len(block) + 64 * CHUNK:
                    raise Failure("Not enough space to complete the DLC download.")
                out.write(block)
                size += len(block)
            if not size or (length and size != length):
                raise Failure("The DLC download is incomplete.")
            return target, {"source_id": identity, "etag": reply.headers.get("ETag"),
                            "last_modified": reply.headers.get("Last-Modified")}
    except HTTPError as error:
        if error.code == 304 and headers:
            return None, previous
        raise Failure(f"DLC download failed (HTTP {error.code}). Check its GIANTS source.") from None
    except (OSError, ValueError):
        raise Failure("DLC download failed. Check connectivity and the GIANTS source.") from None


def verified_cache(work, job):
    if not isinstance(job, dict):
        return None
    name, checksum = job.get("installer"), job.get("sha256")
    match = PACKAGE.fullmatch(name) if isinstance(name, str) else None
    if not match or match[1] != checksum:
        return None
    path = work / name
    if path.is_file() and not path.is_symlink() and digest(path) == checksum:
        return path
    return None


def prepare(work, keys, sources):
    inbox = ROOT / "dlc-installers"
    inbox.mkdir(exist_ok=True)
    old = read_json(work / "pending.json").get("jobs", [])
    if not isinstance(old, list):
        old = []
    jobs, seen, lookups = [], set(), {}
    for alias, key in keys.items():
        print(f"DLC {alias}: checking installation sources.")
        if alias in sources:
            items = [sources[alias]]
        else:
            if key not in lookups:
                lookups[key] = portal_links(key)
            items = lookups[key]
        for source in items:
            identity = hashlib.sha256(source.encode()).hexdigest()
            previous = next((job for job in old if isinstance(job, dict) and
                             job.get("alias") == alias and job.get("source_id") == identity), {})
            cached = verified_cache(work, previous)
            fd, temp_name = tempfile.mkstemp(prefix=f"{alias}-", suffix=".part", dir=work)
            os.close(fd)
            temporary = Path(temp_name)
            try:
                if source.lower().startswith("https://"):
                    path, metadata = fetch(source, temporary, previous if cached else {})
                    if path is None:
                        path = cached
                else:
                    path = uploaded_file(inbox, source)
                    metadata = {"source_id": identity}
                extension, checksum = package_type(path), digest(path)
                if checksum in seen:
                    print(f"DLC {alias}: identical installer already queued.")
                    continue
                destination = work / (checksum + extension)
                if destination.is_symlink():
                    raise Failure("Unexpected link in the DLC cache.")
                if path != destination and (not destination.is_file() or digest(destination) != checksum):
                    if path != temporary:
                        if shutil.disk_usage(work).free < path.stat().st_size + MIN_FREE:
                            raise Failure("Not enough free space to cache the uploaded DLC installer.")
                        shutil.copyfile(path, temporary)
                    os.replace(temporary, destination)
                if digest(destination) != checksum:
                    raise Failure("Cached DLC installer failed its checksum check.")
                seen.add(checksum)
                jobs.append(dict(metadata, alias=alias, installer=destination.name, sha256=checksum))
            finally:
                temporary.unlink(missing_ok=True)
    manifest = {"schema": 1, "configuration": fingerprint(keys, sources), "aliases": sorted(keys), "jobs": jobs}
    save_json(work / "pending.json", manifest)
    print(f"DLC download preparation complete: {len(jobs)} installer(s).")
    return manifest


def prepare_for_reinstall():
    keys, sources, _ = settings()
    if keys:
        with operation() as work:
            prepare(work, keys, sources)


def image_setup(image, directory):
    tool = shutil.which("7z") or shutil.which("7zz")
    if not tool:
        raise Failure("DLC .img sources require 7z in the server image.")
    listing = subprocess.run([tool, "l", "-slt", "-ba", str(image)],
                             capture_output=True, text=True, timeout=120)
    if listing.returncode:
        raise Failure("7z could not read the DLC image.")
    total, entries = 0, 0
    for block in re.split(r"\n\s*\n", listing.stdout):
        fields = dict(line.split(" = ", 1) for line in block.splitlines() if " = " in line)
        if "Path" not in fields:
            continue
        name = fields["Path"].replace("\\", "/")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or ":" in name:
            raise Failure("Unsafe path in the DLC image.")
        if any(("Link" in key or "Reparse" in key) and value.strip()
               for key, value in fields.items() if key != "Links"):
            raise Failure("Links inside DLC images are not supported.")
        size = fields.get("Size", "0")
        if not size.isdecimal():
            raise Failure("Invalid file size in the DLC image.")
        total += int(size)
        entries += 1
    if not 0 < entries <= 10000:
        raise Failure("The DLC image is empty or contains too many files.")
    if shutil.disk_usage(directory).free < total + MIN_FREE:
        raise Failure("Not enough free space to extract the DLC image.")
    result = subprocess.run([tool, "x", "-y", "-o" + str(directory), str(image)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
    if result.returncode:
        raise Failure("DLC image extraction failed.")
    root = directory.resolve()
    files = []
    for path in directory.rglob("*"):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise Failure("Unsafe extracted path in the DLC image.")
        if path.is_file():
            files.append(path)
    setups = [p for p in files if p.name.lower() == "setup.exe"]
    candidates = setups or [p for p in files if p.suffix.lower() == ".exe" and
                            not p.name.lower().startswith(("unins", "autorun"))]
    if len(candidates) != 1 or package_type(candidates[0]) != ".exe":
        raise Failure("The DLC image must contain one unambiguous Windows installer.")
    return candidates[0]


def payload_stats():
    result = {}
    for file in (PROFILE / "pdlc").glob("*.dlc"):
        if file.is_file() and not file.is_symlink():
            info = file.stat()
            result[file.name] = (info.st_size, info.st_mtime_ns)
    return result


def payloads():
    result = {}
    for name, (size, modified) in payload_stats().items():
        if size < 64:
            continue
        file = PROFILE / "pdlc" / name
        with file.open("rb") as stream:
            if b"<dlcstub" in stream.read(4096).lower():
                continue
        result[name] = (digest(file), modified)
    return result


def already_installed(record, prefix_id, current):
    files = record.get("files") if isinstance(record, dict) else None
    return isinstance(files, dict) and bool(files) and record.get("prefix") == prefix_id and all(
        name in current and current[name][0] == checksum for name, checksum in files.items())


def success_candidates(listing):
    stack, matches = [], []
    for line in listing.splitlines():
        match = re.fullmatch(
            r"( *)([0-9a-fA-F]+)\s+(\S+)\s+([0-9a-fA-F]{8})\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+(.*)", line)
        if not match:
            continue
        indent, handle, kind, style, title = match.groups()
        depth, visible = len(indent), bool(int(style, 16) & 0x10000000)
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if kind == "Static" and visible and title.startswith("Installation s") and stack:
            _, parent, parent_kind, parent_visible, parent_title = stack[-1]
            if parent_kind == "#32770" and parent_visible and parent_title.startswith("Farming Simula"):
                matches.append((parent, handle))
        stack.append((depth, handle, kind, visible, title))
    return matches


def success_dialog(tag, env):
    def inspect(command):
        result = subprocess.run([str(proton(tag)), "runinprefix", "winedbg", "--command", command],
                                env=env, capture_output=True, text=True, errors="replace", timeout=20)
        return result.stdout if result.returncode == 0 else ""
    matches = success_candidates(inspect("info wnd"))
    if len(matches) != 1:
        return False
    parent, child = (inspect("info * wnd 0x" + handle) for handle in matches[0])
    return bool(re.search(r"class='#32770'", parent) and re.search(r"text='Farming Simulator 25 - [^']+'", parent)
                and re.search(r"class='Static'", child) and "text='Installation successful.'" in child)


def install_one(installer, key, tag, env, timeout):
    before, before_stats = payloads(), payload_stats()
    process = run_proton(tag, installer, cwd=installer.parent, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    entered, confirmed, next_check = False, False, 0.0
    deadline = time.monotonic() + timeout

    def windows(title):
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", title],
                                env=env, capture_output=True, text=True, timeout=10)
        return [line for line in result.stdout.splitlines() if line.isdigit()]

    def xdo(*args, input=None):
        result = subprocess.run(["xdotool", *args], env=env, input=input, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=15)
        if result.returncode:
            raise Failure("The GIANTS DLC installer dialog could not be controlled.")

    try:
        while process.poll() is None:
            now = time.monotonic()
            if now >= deadline:
                raise Failure("The DLC installer timed out; no installed marker was written.")
            dialogs = windows(r"^FarmingSimulator2025([[:space:]]+v[0-9]+)?$")
            if len(dialogs) == 1 and not entered:
                xdo("windowfocus", "--sync", dialogs[0])
                xdo("key", "--clearmodifiers", "ctrl+a")
                xdo("type", "--clearmodifiers", "--delay", "40", "--file", "-",
                    input=key.replace("-", "").encode("ascii"))
                xdo("key", "--clearmodifiers", "Return")
                entered = True
                print("DLC product key submitted to the GIANTS installer.")
            if now >= next_check and any(before_stats.get(name) != stats
                                         for name, stats in payload_stats().items()):
                next_check = now + 5
                result = windows(r"^Farming Simulator 25 - .+$")
                if len(result) == 1 and success_dialog(tag, env):
                    confirmed = True
                    xdo("windowfocus", "--sync", result[0])
                    xdo("key", "--clearmodifiers", "Return")
            time.sleep(2)
        if process.returncode != 0 and not (process.returncode == 1 and confirmed):
            raise Failure(f"The DLC installer exited with status {process.returncode}; no marker was written.")
        changed = {name: value[0] for name, value in payloads().items() if before.get(name) != value}
        if not changed:
            raise Failure("The DLC installer did not produce a new or updated non-stub payload.")
        return changed
    finally:
        terminate(process)
        stop_wine(tag, env)


def activate_configured(tag, env):
    keys, sources, timeout = settings()
    if not keys:
        return
    prefix = compat(tag) / "pfx"
    profile_path = prefix / "drive_c" / "users" / "steamuser" / "Documents" / "My Games" / "FarmingSimulator2025"
    if not (prefix / "system.reg").is_file() or profile_path.resolve() != PROFILE.resolve():
        raise Failure("The DLC installer must share the persistent FS25 profile and Proton prefix.")
    if not (PROFILE / "AHC_63805.dat").is_file():
        raise Failure("Activate the FS25 base game before installing DLCs.")
    with operation() as work:
        pending = read_json(work / "pending.json")
        if (pending.get("schema") != 1 or pending.get("configuration") != fingerprint(keys, sources)
                or pending.get("aliases") != sorted(keys) or not isinstance(pending.get("jobs"), list)
                or not pending["jobs"]):
            pending = prepare(work, keys, sources)
        token_path = prefix / ".fs25-dlc-prefix-id"
        if not token_path.exists():
            with atomic_file(token_path, encoding="ascii") as out:
                out.write(uuid4().hex)
        token = token_path.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[a-f0-9]{32}", token):
            raise Failure("Invalid DLC identity for this Proton prefix.")
        state = work / "installed.json"
        records = read_json(state).get("installers", {})
        if not isinstance(records, dict):
            records = {}
        current = payloads()
        queue = []
        for job in pending["jobs"]:
            path = verified_cache(work, job)
            if path is None or job.get("alias") not in keys:
                raise Failure("A prepared DLC installer is missing or changed. Run Reinstall to refresh the cache.")
            if already_installed(records.get(job["sha256"]), token, current):
                print(f"DLC {job['alias']}: verified installed payload; skipping setup.")
            else:
                queue.append((job, path))
        if not queue:
            return
        with xvfb("1280x720x24") as display:
            gui = dict(env, DISPLAY=display)
            for job, path in queue:
                alias = job["alias"]
                print(f"DLC {alias}: starting the official GIANTS installer.")
                with tempfile.TemporaryDirectory(prefix="extract-", dir=work) as scratch:
                    exe = image_setup(path, Path(scratch)) if path.suffix == ".img" else path
                    files = install_one(exe, keys[alias], tag, gui, timeout)
                records[job["sha256"]] = {"prefix": token, "files": files}
                save_json(state, {"schema": 1, "installers": records})
                print(f"DLC {alias}: installer completed and payload verified.")
