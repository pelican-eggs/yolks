"""AMP's GIANTS disc download, Proton setup and explicit update stages."""

from contextlib import suppress
import hashlib
from html import unescape
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from urllib.error import URLError
from urllib.parse import unquote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from common import (DEFAULT_PROTON, GAME, MARKER, RELEASE, ROOT, SECRETS, WORK,
                    Failure, atomic_file, panel_setting, product_key, proton, proton_env, run_proton, stop_wine,
                    terminate, valid_game, version, xvfb)


PORTAL = "https://eshop.giants-software.com/downloads.php"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
GIB = 1024 ** 3
CHUNK = 1024 ** 2


def cdn(host):
    return bool(re.fullmatch(r"cdn[0-9]*\.giants-software\.com", host or ""))


def allowed(url, hosts):
    try:
        info = urlsplit(url)
        return (info.scheme == "https" and info.username is None and info.password is None
                and info.port in (443, None) and hosts(info.hostname))
    except ValueError:
        return False


class TrustedRedirect(HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(newurl, self.hosts):
            raise URLError("Unexpected download redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def remote(url, hosts, *, data=None, referer=None, headers=None):
    if not allowed(url, hosts):
        raise Failure("The download URL is not on an allowed HTTPS host.")
    headers = {"User-Agent": UA, **(headers or {})}
    if referer:
        headers["Referer"] = referer
    return build_opener(TrustedRedirect(hosts)).open(Request(url, data, headers), timeout=60)


def lookup(key):
    try:
        with remote(PORTAL, lambda host: host == "eshop.giants-software.com",
                    data=urlencode({"activationKey": key, "foobar": "DOWNLOAD"}).encode()) as reply:
            page = unescape(reply.read(4 * CHUNK).decode("utf-8", "replace"))
    except (OSError, ValueError):
        raise Failure("The GIANTS download portal could not be reached.") from None
    links = sorted(set(re.findall(r'https://cdn[0-9]*\.giants-software\.com/[^"\'<>\s]+', page)))
    for link in links:
        name = Path(unquote(urlsplit(link).path)).name
        if allowed(link, cdn) and re.fullmatch(r"FarmingSimulator25[^/]*\.img", name, re.I):
            return link
    raise Failure("GIANTS returned no FS25 disc download for this product key.")


def download(url, dest, hosts, *, referer=None, progress=False):
    try:
        with remote(url, hosts, referer=referer) as reply, atomic_file(dest, "wb") as out:
            total = reply.headers.get("Content-Length")
            total = int(total) if total and total.isdigit() else None
            size, report = 0, time.monotonic() + 10
            while data := reply.read(CHUNK):
                out.write(data)
                size += len(data)
                if progress and time.monotonic() >= report:
                    suffix = f" of {total / GIB:.2f} GiB ({size / total:.1%})" if total else ""
                    print(f"Downloading: {size / GIB:.2f} GiB{suffix}")
                    report = time.monotonic() + 10
            if not size or total is not None and size != total:
                raise Failure("The download did not contain the expected number of bytes.")
    except (OSError, ValueError):
        raise Failure(f"Download failed for {dest.name}.") from None


def ensure_proton(tag):
    exe = proton(tag)
    if exe.is_file() and os.access(exe, os.X_OK):
        return
    major, minor = map(int, RELEASE.fullmatch(tag).groups())
    asset = tag + ("-x86_64" if (major, minor) >= (11, 4) else "")
    origin = f"https://github.com/GloriousEggroll/proton-ge-custom/releases/download/{tag}/{asset}"
    hosts = lambda host: host in {"github.com", "release-assets.githubusercontent.com",
                                  "objects.githubusercontent.com"}
    exe.parent.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {tag} for linux/amd64.")
    with tempfile.TemporaryDirectory(prefix="proton-", dir=WORK) as scratch:
        scratch = Path(scratch)
        archive, checksum = scratch / "proton.tar.gz", scratch / "proton.sha512sum"
        download(origin + ".sha512sum", checksum, hosts)
        with checksum.open(encoding="ascii") as handle:
            match = re.match(r"^([0-9a-fA-F]{128})(?:\s|$)", handle.read(4096))
        if not match:
            raise Failure("GE-Proton returned an invalid SHA-512 checksum.")
        download(origin + ".tar.gz", archive, hosts, progress=True)
        with archive.open("rb") as stream:
            if hashlib.file_digest(stream, "sha512").hexdigest() != match[1].lower():
                raise Failure("GE-Proton archive checksum mismatch.")
        extracted = scratch / "extracted"
        with tarfile.open(archive, "r:gz") as pack:
            pack.extractall(extracted, filter="data")
        roots = [entry for entry in extracted.iterdir() if (entry / "proton").is_file()]
        if len(roots) != 1 or not os.access(roots[0] / "proton", os.X_OK):
            raise Failure("GE-Proton archive has no executable Proton launcher.")
        if exe.parent.exists():
            shutil.rmtree(exe.parent)
        roots[0].rename(exe.parent)


def extract_iso(image, destination):
    """Extract the primary ISO9660 root, matching the GIANTS installer layout in AMP."""
    sector = 2048
    size = image.stat().st_size
    with image.open("rb") as disc:
        def read_at(offset, length):
            if offset < 0 or offset + length > size:
                raise Failure("Truncated or invalid ISO9660 extent.")
            disc.seek(offset)
            data = disc.read(length)
            if len(data) != length:
                raise Failure("Truncated ISO9660 image.")
            return data

        def u32(data, offset):
            return int.from_bytes(data[offset:offset + 4], "little")

        descriptor = read_at(16 * sector, sector)
        if descriptor[:7] != b"\x01CD001\x01":
            raise Failure("The GIANTS download is not an ISO9660 disc image.")
        directory_size = u32(descriptor, 166)
        if not 0 < directory_size <= 64 * CHUNK:
            raise Failure("Invalid ISO9660 root directory size.")
        directory = read_at(u32(descriptor, 158) * sector, directory_size)
        position, continued = 0, None
        while position < len(directory):
            length = directory[position]
            if length == 0:
                position = (position // sector + 1) * sector
                continue
            record = directory[position:position + length]
            position += length
            if len(record) < 34 or len(record) != length or record[32] > length - 33:
                raise Failure("Invalid ISO9660 directory record.")
            flags, name = record[25], record[33:33 + record[32]]
            if flags & 2 or name in (b"\x00", b"\x01"):
                continue
            try:
                name = name.decode("ascii").split(";", 1)[0].removesuffix(".")
            except UnicodeError:
                raise Failure("Non-ASCII name in the primary ISO9660 directory.") from None
            if not name or name in (".", "..") or "/" in name or "\\" in name or "\x00" in name:
                raise Failure("Invalid filename in the ISO9660 image.")
            if continued is not None and continued != name:
                raise Failure("Missing ISO9660 multi-extent continuation.")
            offset, remaining = u32(record, 2) * sector, u32(record, 10)
            with (destination / name).open("ab" if continued else "xb") as out:
                while remaining:
                    count = min(remaining, CHUNK)
                    out.write(read_at(offset, count))
                    offset += count
                    remaining -= count
            continued = name if flags & 128 else None
        if continued is not None:
            raise Failure("Incomplete ISO9660 multi-extent file.")


def installed():
    try:
        state = json.loads(MARKER.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None
    if (not isinstance(state, dict) or not isinstance(state.get("source"), str)
            or not state["source"] or not valid_game(GAME)):
        return None
    version(state.get("proton"))
    return state


def check_space(gib):
    free = shutil.disk_usage(WORK).free
    if free < gib * GIB:
        raise Failure(f"Only {free / GIB:.1f} GiB free; this install needs about {gib} GiB.")


def setup_executable(unpacked):
    return next((item for item in unpacked.iterdir()
                 if item.name.lower() == "setup.exe" and item.is_file() and item.stat().st_size), None)


def unpack(url, source):
    output = WORK / "fs25_unpack"
    stamp = output / ".source"
    if stamp.is_file() and stamp.read_text(encoding="utf-8") == source and setup_executable(output):
        check_space(45)
        print("Reusing the previously verified disc extraction.")
        return output
    check_space(70)
    if output.exists():
        shutil.rmtree(output)
    image = WORK / "fs25_download.img"
    image.unlink(missing_ok=True)
    try:
        print("Downloading the FS25 disc image from GIANTS.")
        download(url, image, cdn, referer=PORTAL, progress=True)
        print("Extracting the ISO9660 installer.")
        with tempfile.TemporaryDirectory(prefix="disc-", dir=WORK) as scratch:
            stage = Path(scratch) / "root"
            stage.mkdir()
            extract_iso(image, stage)
            if not setup_executable(stage):
                raise Failure("The FS25 disc does not contain Setup.exe.")
            for entry in stage.iterdir():
                if entry.suffix.lower() == ".bin" and "_" in entry.name:
                    alias = entry.with_name(entry.name.replace("_", "-"))
                    with suppress(FileExistsError):
                        os.link(entry, alias)
            (stage / ".source").write_text(source, encoding="utf-8")
            stage.rename(output)
    finally:
        image.unlink(missing_ok=True)
    return output


def winpath(path):
    return "Z:" + str(path).replace("/", "\\")


def run_setup(setup, tag):
    env = proton_env(tag)
    log = WORK / "fs25_install.log"
    console = WORK / "fs25_proton.log"
    print("Installing FS25 through GE-Proton. ( This can take a long while, ITS NOT STUCK JUST WAIT )")
    with xvfb() as display, console.open("wb") as out:
        env["DISPLAY"] = display
        process = run_proton(tag, setup, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                             "/NOCANCEL", "/SP-", f"/DIR={winpath(GAME)}", f"/LOG={winpath(log)}",
                             env=env, cwd=setup.parent, stdout=out, stderr=subprocess.STDOUT)
        try:
            result = process.wait(timeout=4 * 3600)
        finally:
            terminate(process)
            stop_wine(tag, env)
    if result or not valid_game(GAME):
        raise Failure(f"FS25 setup failed (exit {result}); see work/fs25_install.log and work/fs25_proton.log.")


def drop_volume_root():
    if os.geteuid() != 0:
        return
    owner = ROOT.stat()
    if owner.st_uid == 0:
        raise Failure("The data volume must belong to the non-root Wings server UID/GID.")
    os.setgroups([])
    os.setgid(owner.st_gid)
    os.setuid(owner.st_uid)


def install(*, require_game=False):
    drop_volume_root()
    os.umask(0o077)
    SECRETS.mkdir(mode=0o700, exist_ok=True)
    WORK.mkdir(exist_ok=True)
    previous = WORK / "previous-game"
    if previous.exists():
        if installed():
            shutil.rmtree(previous)
        else:
            if GAME.exists():
                shutil.rmtree(GAME)
            previous.rename(GAME)
    old = installed()
    key = product_key()
    override = panel_setting("FS25_DOWNLOAD_URL", "download-url")
    if not key and not override:
        if old:
            print("No product key or override available; leaving the installed game unchanged.")
        elif require_game:
            raise Failure("Set GIANTS Product Key in the server's Admin Startup settings, then start again.")
        else:
            print("Volume initialized. Set GIANTS Product Key, then start the server.")
        return
    tag = version(os.environ.get("FS25_PROTON_VERSION", "").strip() or DEFAULT_PROTON)
    url = override or lookup(key)
    source = Path(unquote(urlsplit(url).path)).name
    if not allowed(url, cdn) or not source.lower().endswith(".img"):
        raise Failure("The override must be an HTTPS .img link from the GIANTS CDN.")
    if old and old["source"] == source:
        if old["proton"] != tag or not proton(tag).is_file():
            check_space(3)
            ensure_proton(tag)
            with atomic_file(MARKER, encoding="utf-8") as out:
                json.dump({"source": source, "proton": tag}, out)
            print(f"Using {tag}; the game disc has not changed.")
        else:
            print("This FS25 disc is already installed. Nothing to update.")
        return

    extracted = unpack(url, source)
    ensure_proton(tag)
    if GAME.exists():
        GAME.rename(previous)
    try:
        GAME.mkdir()
        run_setup(setup_executable(extracted), tag)
        for name in ("dedicatedServer.xml", "cert.pem", "pk.pem"):
            if (previous / name).is_file():
                shutil.copy2(previous / name, GAME / name)
        with atomic_file(MARKER, encoding="utf-8") as out:
            json.dump({"source": source, "proton": tag}, out)
    except BaseException:
        if GAME.exists():
            shutil.rmtree(GAME)
        if previous.exists():
            previous.rename(GAME)
        raise
    if previous.exists():
        shutil.rmtree(previous)
    shutil.rmtree(extracted)
    print(f"Installed {source} with {tag}.")
