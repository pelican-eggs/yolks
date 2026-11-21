FROM        --platform=$TARGETOS/$TARGETARCH debian:13-slim

LABEL       org.opencontainers.image.authors="DasEric" \
            org.opencontainers.image.source="https://github.com/pelican-eggs/yolks" \
            org.opencontainers.image.licenses=MIT

RUN         dpkg --add-architecture i386 \
            && apt-get update \
            && apt-get install -y --no-install-recommends \
                ca-certificates python3 tini procps p7zip-full \
                xvfb xauth xdotool fonts-liberation \
                libatomic1 libasound2t64 libdbus-1-3 libfontconfig1 libfreetype6 \
                libgl1 libgnutls30t64 libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 \
                libpulse0 libsdl2-2.0-0 libunwind8 libvulkan1 mesa-vulkan-drivers \
                libxcomposite1 libxcursor1 libxfixes3 libxi6 libxinerama1 libxrandr2 libxrender1 libxxf86vm1 \
                libc6:i386 libfontconfig1:i386 libfreetype6:i386 libgcc-s1:i386 libstdc++6:i386 \
                libx11-6:i386 libxext6:i386 libxrender1:i386 \
            && rm -rf /var/lib/apt/lists/* \
            && useradd --create-home --user-group --home-dir /home/container --shell /bin/bash container \
            && mkdir -p /mnt && ln -s /home/container /mnt/server

COPY        fs25/ /opt/fs25/
COPY        LICENSE /usr/share/doc/fs25/LICENSE
ENV         USER=container HOME=/home/container PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR     /home/container

# Wings selects the runtime UID. The install command drops to the server volume owner.
USER        0
STOPSIGNAL  SIGTERM
ENTRYPOINT  ["/usr/bin/tini", "--"]
CMD         ["/usr/bin/python3", "/opt/fs25/server.py", "start"]
