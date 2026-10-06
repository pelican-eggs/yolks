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

## Configuration ownership

The game and web ports are always synchronized with the Pelican allocations.
All other optional server variables use the following rule:

- an empty variable preserves the value saved in the GIANTS Web Interface;
- a non-empty variable is an explicit panel override and is applied on every
  container start.

On a new installation the image creates the minimum configuration required by
GIANTS. The initial web login is `admin` / `webpassword`; change it in the
GIANTS Web Interface. Existing XML files are backed up as `*.xml.bak` before a
changed version is written.

Images published before this behavior used a one-year Web API interval. That
generated value is migrated once to 60 seconds so connected-player data is
updated in a useful time. Afterwards, the value selected in the GIANTS Web
Interface is preserved.

## Persistent data

```text
Game:       /home/container/game/Farming Simulator 2025
Config:     /home/container/config/FarmingSimulator2025
Mods:       /home/container/config/FarmingSimulator2025/mods
Savegames:  /home/container/config/FarmingSimulator2025/savegameN
DLC data:   /home/container/config/FarmingSimulator2025/pdlc
Installers: /home/container/installer
Logs:       /home/container/logs
Game log:   /home/container/config/FarmingSimulator2025/log.txt
```

Upload mod ZIP files without extracting them. To migrate a savegame, stop the
server and copy the complete contents of the existing savegame into the target
`savegameN` directory, where `N` matches `SAVEGAME_INDEX`.

## Mod-map startup time

FS25 validates every ZIP in the active `mods` directory before loading the map.
Large maps also need additional time for map data, textures, shaders and the
savegame. Keep only the map and its required dependencies in the active mod
directory while diagnosing a slow start. Compare the first and second start
with the same files; persistent configuration and Wine data are not deleted by
the image between starts.

Use `/home/container/config/FarmingSimulator2025/log.txt` to distinguish mod
validation from map or savegame loading. Fix all `Error:` entries and test the
same save with the built-in map before attributing a delay to the container.

## Player status and pause-when-empty

Set **Pause Game If Empty** in the GIANTS Web Interface and leave
`SERVER_PAUSE` empty if GIANTS should manage it. `SERVER_STATS_INTERVAL`
controls the Link XML/Web API refresh interval; it does not replace the game
engine's disconnect timeout. The game allocation must be exposed as both TCP
and UDP, and only one game process should be started for a server instance.
