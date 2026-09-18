FROM        --platform=$TARGETOS/$TARGETARCH debian:13-slim

LABEL       author="Michael Parker" maintainer="parker@pterodactyl.io"

LABEL       org.opencontainers.image.source="https://github.com/pterodactyl/yolks"
LABEL       org.opencontainers.image.licenses=MIT

ENV         DEBIAN_FRONTEND=noninteractive

RUN         useradd -m -d /home/container -s /bin/bash container

RUN         ln -s /home/container/ /nonexistent

ENV         USER=container HOME=/home/container

## Install dependencies
RUN         apt update && apt install -y --no-install-recommends \
                # packages for startup
                tini \
                # certificate and signature
                ca-certificates gnupg2 libssl-dev \
                # glib and gcc related packages
                gcc g++ libgcc-12-dev libc++-dev libc6 libstdc++6 \
                # downloading
                git wget curl \
                # extraction and compression
                tar zip unzip binutils xz-utils liblzo2-2 cabextract libzip5 libzadc4 \
                # network tools
                iproute2 net-tools telnet \
                # locale and timezone
                locales icu-devtools tzdata \
                # database compat
                sqlite3 libsqlite3-dev libmariadb-dev-compat \
                # aditional libraries
                libduktape207 liblua5.3-0 libz3-dev rapidjson-dev libevent-dev libzip5 libprotobuf32t64 libatomic1 libunwind8

# Temp fix for libicu66.1 for RAGE-MP and libssl1.1 for fivem and many more
RUN         if [ "$(uname -m)" = "x86_64" ]; then \
                wget http://archive.ubuntu.com/ubuntu/pool/main/i/icu/libicu66_66.1-2ubuntu2.1_amd64.deb && \
                wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2.24_amd64.deb && \
                dpkg -i libicu66_66.1-2ubuntu2.1_amd64.deb && \
                dpkg -i libssl1.1_1.1.1f-1ubuntu2.24_amd64.deb && \
                rm libicu66_66.1-2ubuntu2.1_amd64.deb libssl1.1_1.1.1f-1ubuntu2.24_amd64.deb; \
            fi
# ARM64
RUN         if [ ! "$(uname -m)" = "x86_64" ]; then \
                wget http://ports.ubuntu.com/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_arm64.deb && \
                dpkg -i libssl1.1_1.1.1f-1ubuntu2_arm64.deb && \
                rm libssl1.1_1.1.1f-1ubuntu2_arm64.deb; \
            fi

## Configure locale
RUN         update-locale lang=en_US.UTF-8 \
            && dpkg-reconfigure --frontend noninteractive locales


WORKDIR     /home/container

STOPSIGNAL  SIGINT

COPY        --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT  ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
