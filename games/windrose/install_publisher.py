"""Install Windrose from the original, digest-pinned public publisher layer."""

import copy
import hashlib
import json
import os
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

REPO = "windroseserver/windroseserver"
LAYER = "d9ce14ee610d68bb2068359a568305f8b9b351834fb11d959f584022628c7b25"
SIZE = 2118970930
PREFIX = "home/ue_user/app/"
BINARY = "R5/Binaries/Linux/WindroseServer-Linux-Shipping"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        return None


def download(target):
    # Registry credentials never go to the redirected download host.
    token_url = "https://auth.docker.io/token?" + urllib.parse.urlencode({
        "service": "registry.docker.io",
        "scope": f"repository:{REPO}:pull",
    })
    with urllib.request.urlopen(token_url, timeout=30) as response:
        token = json.loads(response.read(65536))["token"]
    registry = urllib.request.Request(
        f"https://registry-1.docker.io/v2/{REPO}/blobs/sha256:{LAYER}",
        headers={"Authorization": "Bearer " + token},
    )
    opener = urllib.request.build_opener(NoRedirect())
    try:
        response = opener.open(registry, timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code not in (302, 303, 307, 308):
            raise
        location = exc.headers.get("Location", "")
        if urllib.parse.urlsplit(location).scheme != "https":
            raise ValueError("Registry returned an invalid publisher download URL.") from None
        response = urllib.request.urlopen(location, timeout=60)
    digest = hashlib.sha256()
    seen = 0
    with response, target.open("xb") as out:
        while chunk := response.read(1024 * 1024):
            seen += len(chunk)
            if seen > SIZE:
                raise ValueError("Publisher layer exceeds its pinned size.")
            digest.update(chunk)
            out.write(chunk)
    if seen != SIZE or digest.hexdigest() != LAYER:
        raise ValueError("Publisher layer did not match its pinned size and digest.")


def extract_game(archive, destination):
    with tarfile.open(archive, "r:gz") as game:
        for member in game:
            name = member.name.removeprefix("./").lstrip("/")
            if not name.startswith(PREFIX):
                continue
            path = PurePosixPath(name[len(PREFIX):])
            if path == PurePosixPath("."):
                continue
            if ".." in path.parts:
                raise ValueError("Unsafe publisher game path.")
            if path.parts[:2] in (("R5", "Saved"), ("R5", "ServerDescription.json")):
                continue
            # The pinned publisher copy layer only contains directories and regular files.
            if not (member.isdir() or member.isfile()):
                raise ValueError("Unsupported publisher game archive entry.")
            entry = copy.copy(member)
            entry.name = str(path)
            game.extract(entry, destination, filter="data")
    executable = destination / BINARY
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError("The publisher's Linux game executable is missing or not executable.")
    crashpad = destination / "R5/Plugins/3rdParty/Sentry/Binaries/Linux/crashpad_handler"
    if crashpad.is_file():
        crashpad.chmod(crashpad.stat().st_mode | 0o111)
    (destination / "R5/Saved").symlink_to("../../R5/Saved")
    (destination / "R5/ServerDescription.json").symlink_to("../../R5/ServerDescription.json")
    (destination / ".publisher-layer").write_text(LAYER + "\n", encoding="utf-8")


def install(destination):
    game = destination / ".windrose-game"
    if game.exists() or game.is_symlink():
        if not game.is_symlink() and (game / ".publisher-layer").read_text().strip() == LAYER and os.access(game / BINARY, os.X_OK):
            return
        raise ValueError("An existing game install did not match the pinned layer.")
    with tempfile.TemporaryDirectory(prefix=".windrose-install-", dir=destination) as temporary:
        path = Path(temporary)
        layer = path / "publisher.tar.gz"
        download(layer)
        extracted = path / "game"
        extracted.mkdir()
        extract_game(layer, extracted)
        extracted.rename(game)


if __name__ == "__main__":
    try:
        install(Path(sys.argv[1]).resolve(strict=True))
    except (OSError, ValueError, KeyError, tarfile.TarError) as exc:
        # Avoid including registry headers, signed redirect URLs or tokens in logs.
        print(f"Windrose publisher installation failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
    print("Windrose publisher Linux files installed from the verified layer.")
