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

## Installation workflow

1. Upload an official FS25 installer (`.exe`, `.img`, `.iso` or `.zip`) to
   `/home/container/installer`.
2. Start the container and open the noVNC address printed in the console.
3. Open **Install / activate FS25** on the desktop, or enable `AUTO_INSTALL`.
4. Enter the dedicated-server product key during activation.
5. The full game is launched once by the installation process to finish
   activation. Quit the game afterwards, or restart the container if it stays
   open.
6. After a successful installation, delete the contents of
   `/home/container/installer` to reclaim disk space.

The first game-server start from the GIANTS Web Interface can take several
minutes. This longer delay is expected only on the first start.

## Persistent data

```text
Game:       /home/container/game/Farming Simulator 2025
Config:     /home/container/config/FarmingSimulator2025
Mods:       /home/container/config/FarmingSimulator2025/mods
Savegames:  /home/container/config/FarmingSimulator2025/savegameN
DLC data:   /home/container/config/FarmingSimulator2025/pdlc
Installers: /home/container/installer
Logs:       /home/container/logs
```

Upload mod ZIP files without extracting them. To migrate a savegame, stop the
server and copy the complete contents of the existing savegame into the target
`savegameN` directory, where `N` matches `SAVEGAME_INDEX`.
