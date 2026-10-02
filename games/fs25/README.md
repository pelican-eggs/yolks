# Farming Simulator 25

Pelican/Pterodactyl runtime image for the Farming Simulator 25 dedicated
server. The image contains Wine 11, an XFCE desktop, TigerVNC, noVNC and the
runtime helpers needed for installation, activation and DLC installation.

The container runs as the unprivileged `container` user. Persistent game data,
configuration, the Wine prefix, installers and logs are stored below
`/home/container`.

## Image

```text
ghcr.io/pelican-eggs/games:fs25
```

The image is currently built for `linux/amd64`.

## Startup

The egg startup command directly launches the GIANTS dedicated server through
Wine:

```text
wine "/home/container/game/Farming Simulator 2025/dedicatedServer.exe"
```

Container initialization and the graphical installation environment are
provided by the immutable image entrypoint. No startup files are generated in
the server's writable data directory.
