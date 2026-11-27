# Windrose native Linux runtime

Linux amd64 only. The Yolk contains the launcher, first-run helper, and an installer that fetches the publisher's original Linux server layer directly from Docker Hub. It has no game files or launcher patches. The publisher layer is pinned and verified at installation, then the unchanged game is placed in the server volume. The underlying Windrose publisher release is 0.10.0.9.32-22d39a16.

The Pelican installer invokes the same image with `bash /mnt/install/install.sh`. The game runtime runs under the non-root Wings UID. Config and saves stay in `/home/container`. The installer does not require registry credentials. Direct IP uses the primary allocation. This does not cover the publisher's invite-code or ARM paths.

The provenance of the adapter files is [the public reviewed source at f44b474](https://github.com/TheIlluminate92/windrose-pelican/tree/f44b47499c8294e7abd7651617408f1f5f49b731). The Windrose egg upstream attribution and license are preserved. OpenAI Codex assisted with the implementation and verification.

The [community build's CI](https://github.com/TheIlluminate92/windrose-pelican/actions/runs/45924264396) tested the installer, actual Linux gameplay readiness, and first-run backup/edit/reopen workflow. The preceding public build was installed through Pelican and a Direct IP player join was confirmed. The exact Yolks-native recipe still needs its own image build and Panel acceptance. The publisher executable can exit 139 after a normal shutdown request, including under its original image. Successful backup and restore were verified separately.
