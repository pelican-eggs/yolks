FROM    --platform=$TARGETOS/$TARGETARCH node:24-bookworm-slim

LABEL   org.opencontainers.image.source="https://github.com/pelican-eggs/yolks"
LABEL   org.opencontainers.image.licenses=AGPL-3.0-or-later

ENV     DEBIAN_FRONTEND=noninteractive

# Node.js with the SteamCMD runtime, for Brickadia/Omegga and other node-wrapped Steam servers.
# steamcmd is 32-bit and installs itself into the server volume, so only its runtime is needed here.
# build-essential and python3 are for node-gyp: packages with native modules are built in the server container.
RUN     dpkg --add-architecture i386 \
          && apt update \
          && apt upgrade -y \
          && apt install -y lib32gcc-s1 lib32stdc++6 libsdl2-2.0-0:i386 ca-certificates curl wget tar zip unzip git iproute2 net-tools netcat-openbsd telnet tzdata locales tini \
          && apt install -y build-essential python3 sqlite3 libsqlite3-dev procps \
          && useradd -d /home/container -m container

# Set the locale
RUN     sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
          && locale-gen
ENV     LANG=en_US.UTF-8
ENV     LANGUAGE=en_US:en
ENV     LC_ALL=en_US.UTF-8

## install rcon
RUN         cd /tmp/ \
            && curl -sSL https://github.com/gorcon/rcon-cli/releases/download/v0.10.3/rcon-0.10.3-amd64_linux.tar.gz > rcon.tar.gz \
            && tar xvf rcon.tar.gz \
            && mv rcon-0.10.3-amd64_linux/rcon /usr/local/bin/

USER    container
ENV     USER=container HOME=/home/container
WORKDIR /home/container

STOPSIGNAL SIGINT

COPY        --chown=container:container ../entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT    ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
