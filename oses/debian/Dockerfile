FROM         --platform=$TARGETOS/$TARGETARCH debian:bookworm-slim

LABEL        author="Michael Parker" maintainer="parker@pterodactyl.io"

LABEL        org.opencontainers.image.source="https://github.com/pterodactyl/yolks"
LABEL        org.opencontainers.image.licenses=MIT

ENV          DEBIAN_FRONTEND=noninteractive

RUN          useradd -m -d /home/container -s /bin/bash container

RUN          ln -s /home/container/ /nonexistent

ENV          USER=container HOME=/home/container

## Update base packages
RUN          apt update \
             && apt upgrade -y

## Install dependencies
RUN          apt install -y make gcc g++ libgcc-12-dev libc++-dev gdb libc6 git wget curl tar zip unzip binutils xz-utils liblzo2-2 cabextract iproute2 net-tools netcat-traditional telnet libatomic1 libsdl1.2debian libsdl2-2.0-0 \
             libfontconfig1 icu-devtools libunwind8 libssl-dev sqlite3 libsqlite3-dev libmariadb-dev-compat libduktape207 locales ffmpeg gnupg2 apt-transport-https software-properties-common ca-certificates \
             liblua5.3-0 libz3-dev libzadc4 rapidjson-dev tzdata libevent-dev libzip4 libprotobuf32 libfluidsynth3 procps libstdc++6 tini

# Temp fix for libicu66.1 for RAGE-MP and libssl1.1 for fivem and many more
RUN         if [ "$(uname -m)" = "x86_64" ]; then \
                wget http://archive.ubuntu.com/ubuntu/pool/main/i/icu/libicu66_66.1-2ubuntu2.1_amd64.deb && \
                wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.0g-2ubuntu4_amd64.deb && \
                dpkg -i libicu66_66.1-2ubuntu2.1_amd64.deb && \
                dpkg -i libssl1.1_1.1.0g-2ubuntu4_amd64.deb && \
                rm libicu66_66.1-2ubuntu2.1_amd64.deb libssl1.1_1.1.0g-2ubuntu4_amd64.deb; \
            fi
# ARM64
RUN         if [ ! "$(uname -m)" = "x86_64" ]; then \
                wget http://ports.ubuntu.com/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_arm64.deb && \
                dpkg -i libssl1.1_1.1.1f-1ubuntu2_arm64.deb && \
                rm libssl1.1_1.1.1f-1ubuntu2_arm64.deb; \
            fi

## Configure locale
RUN          update-locale lang=en_US.UTF-8 \
             && dpkg-reconfigure --frontend noninteractive locales


WORKDIR     /home/container

STOPSIGNAL SIGINT

COPY        --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT    ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
