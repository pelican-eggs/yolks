# Farming Simulator 25

Pelican/Pterodactyl runtime image for the Farming Simulator 25 dedicated
server. The image contains a source-built Wine-Proton 11 runtime, WineHQ 11 as
a compatibility option, an XFCE desktop, TigerVNC, noVNC and the
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

### Portable Wine synchronization

The default runtime is built from Valve's Wine-Proton 11 source at commit
`dc26e61847081a1b5cb0733dc30feba6ee575482`. Wine 11's supported WoW64 mode
runs both 64-bit and 32-bit Windows programs against the Pelican Wine 11 image's
64-bit Debian libraries, retaining the existing `win64` prefix format. No Steam
launcher, external image entrypoint or additional server startup script is used.
The build checks prefix initialization and both Windows command interpreters
as the unprivileged container user before publishing the image.

In `auto` mode, the controller checks `futex_waitv` and usable shared memory
inside an isolated child before any Wine process starts. A compatible container
can use FSYNC without `/dev/ntsync`, privileged mode, a kernel upgrade or Wings
changes. An unsupported or blocked syscall, failed probe or unavailable shared
memory disables FSYNC instead of preventing startup. Wine can prefer NTSync
when that device is already accessible; otherwise it uses eligible FSYNC or
ordinary server-side synchronization. ESYNC is not part of this Wine branch.

The console reports the selected runtime and FSYNC eligibility, not a claimed
active backend. `diagnose` also inspects the current Wine/game process file
descriptors. `FSYNC shared-memory descriptor observed` or `NTSync device
descriptor observed` provides runtime evidence; missing/inaccessible descriptors
are inconclusive. Old log messages and an environment flag alone are not proof.

Existing servers do not need an egg reimport. To override the defaults, stop
the container and create `/home/container/config/wine-runtime.json` in the
Pelican file manager, then restart the container. For example:

```json
{"runtime": "proton", "sync": "auto"}
```

- `runtime`: `proton` (default) or `stable` (the existing WineHQ 11 runtime).
- `sync`: `auto` (default), `fsync` (try FSYNC without NTSync, fall back if the
  probe fails), or `server` (disable the accelerated backends in Wine-Proton).
- Optional environment variables `FS25_WINE_RUNTIME` and `FS25_WINE_SYNC`
  override the respective file values when non-empty.
- Selection happens once per container lifetime and is inherited by desktop,
  installer and GIANTS child processes. Editing the file requires a full
  container restart, not only stopping/starting the game in GIANTS.

For a controlled comparison, first test `proton`/`auto`, then `proton`/`server`
with a container restart between them. This separates synchronization from the
Wine build change. If a compatibility regression occurs, use `stable`/`server`
with the prefix/configuration backup made before the runtime upgrade. Neither
this runtime nor FSYNC guarantees Windows-equivalent mod-map loading times.

### Wine source and license

The image's controller is MIT-licensed. Wine is LGPL-2.1-or-later; the pinned
upstream source archive, `COPYING.LIB`, `LICENSE` and `AUTHORS` are bundled in
`/opt/fs25/wine-source`. The only source overlay is `VERSION.fs25`, also bundled
there. It identifies this build as `11.0-fs25-proton-dc26e61`, distinct from
WineHQ 11. Wine's normal prefix-update mechanism remains in use; the runtime
selector does not reset activation or game settings. The Dockerfile pins the source commit,
verifies the archive's SHA-256 and applies the version overlay before building.
It also contains the configure/compiler
options. Generic CPU targets are used, never `-march=native`. Development
packages and intermediate objects remain in the build stage, not the final image.

References: [Wine 11 release notes](https://github.com/wine-mirror/wine/blob/wine-11.0/ANNOUNCE.md),
[pinned Wine-Proton source](https://github.com/ValveSoftware/wine/tree/dc26e61847081a1b5cb0733dc30feba6ee575482),
[FSYNC implementation](https://github.com/ValveSoftware/wine/blob/dc26e61847081a1b5cb0733dc30feba6ee575482/server/fsync.c),
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
