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

The GIANTS Web Interface and the actual game server have separate startup
phases. `FS25 image ready.` only indicates container initialization. Large
mod maps can take several minutes to load on any start, not only the first
one. Wait until the game server is available before trying to join.

## Terminal access

Open **Terminal** on the noVNC desktop or select **Terminal** in the applications
menu. The image uses XTerm with an interactive Bash shell. Each terminal opens
its own window instead of depending on an existing D-Bus terminal process.
**Alt+F2** opens the application finder; enter `xterm` to open another terminal.

The image sets the XFCE default terminal and refreshes its terminal desktop/menu
launchers before the desktop starts. Existing browser preferences are preserved;
changed terminal preference files are backed up once with a `.bak` suffix.
The installation, activation, web-server and DLC shortcuts also use XTerm and
keep their window open after the command finishes so its output remains visible.

Existing servers need a rebuilt image: pull the new image and restart the
container. No egg reimport or game reinstallation is required. Mods, savegames,
GIANTS settings and the Wine prefix are not changed by the terminal setup.

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

Measure from clicking **Start** in GIANTS until the game server is joinable,
not until the Web Interface opens. Compare at least three runs using the same
FS25 version, DLCs, mod ZIPs, selected map and a copy of the same savegame.
Separate the first load from subsequent loads, and record the CPU model and
storage used by the Windows and Linux systems. Six allocated CPU equivalents
do not guarantee that a sequential loading stage can use all six at once.

The runtime launches `dedicatedServer.exe` from the game directory and applies
the headless Wine environment before the first Wine process starts, including
with an existing prefix. A low open-file soft limit is raised to at most
65,536, never beyond the inherited hard limit. Existing higher limits remain
unchanged. These changes remove runtime inconsistencies; they do not guarantee
a particular loading-time reduction.

### Capture an ongoing game load

After pulling the updated image, start the game server in GIANTS. While its
map is still loading, open **Terminal** in noVNC and run this manual command:

```text
/opt/fs25/fs25ctl.py diagnose --seconds 10
```

This command is part of the existing image controller, not an additional
startup script. It runs only when invoked and does not prepare the prefix,
rewrite configuration, restart Wine, or change mods, savegames or caches.
It reports the Wine version, CPU affinity, CPU cgroup limits and counters
before/after a bounded `pidstat` sample, process/thread CPU and disk I/O,
game-process open-file limits/counts and the largest i3d loading times in the last
256 KiB of `/home/container/config/FarmingSimulator2025/log.txt`.
The log timings are historical and may precede the current sample. Run the
command again if the game process starts after the initial PID lookup.

Interpret the output alongside the complete game log:

- A busy individual game thread can indicate a sequential CPU-bound stage.
- A busy `wineserver` makes Wine synchronization a candidate for further tests;
  it does not prove that synchronization is the only bottleneck.
- Increasing CPU throttling counters show that the cgroup hit its quota.
  They do not measure all forms of host CPU contention.
- Disk reads, major faults and I/O delays help identify storage activity.
  Zero disk reads can also mean files were served from the page cache; zero
  I/O delay is inconclusive when the kernel does not collect delay accounting.
- The displayed open-file limits belong to the sampled processes. Raising a
  limit is useful only if that limit was constraining the workload.

Wine 11 can use NTSync when built with support and provided with a compatible
host driver and access to `/dev/ntsync`. Kernel support is included from Linux
6.14 (or an appropriate distribution backport). Device accessibility alone
does not prove that the installed Wine build uses it. An image or egg setting
cannot by itself expose a host device through Wings. The image does not enable
unverified ESYNC/FSYNC switches or change the host kernel.

References: [Wine 11 release notes](https://github.com/wine-mirror/wine/blob/wine-11.0/ANNOUNCE.md),
[Linux NTSync driver](https://docs.kernel.org/userspace-api/ntsync.html),
[pidstat manual](https://man7.org/linux/man-pages/man1/pidstat.1.html).

Keep the complete mod set for the initial Windows/Linux comparison. For later
mod isolation, use a separate test copy and remove only optional mods after
checking savegame dependencies. Use a new savegame for a built-in-map reference;
do not change the map of an existing mod-map save. Review `Error:` entries in
the game log. The image preserves persistent configuration, Wine data and game
caches between starts and never extracts or preloads mod ZIPs during startup.

### Validate and roll back an image change

Before testing another Wine image, stop the container and back up the Wine
prefix, configuration and savegame. Record the old image digest. After pulling
the new image, test join/rejoin, save/load, normal stop/restart, noVNC, DLCs and
retained GIANTS settings in addition to measuring map startup. If reverting a
Wine upgrade, stop the container, select the old image and restore its matching
prefix/configuration backup rather than using an upgraded prefix blindly.

## Player status and pause-when-empty

Set **Pause Game If Empty** in the GIANTS Web Interface and leave
`SERVER_PAUSE` empty if GIANTS should manage it. `SERVER_STATS_INTERVAL`
controls the Link XML/Web API refresh interval; it does not replace the game
engine's disconnect timeout. The game allocation must be exposed as both TCP
and UDP, and only one game process should be started for a server instance.
