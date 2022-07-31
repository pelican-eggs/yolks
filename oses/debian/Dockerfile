FROM         --platform=$TARGETOS/$TARGETARCH debian:bullseye-slim

LABEL        author="Michael Parker" maintainer="parker@pterodactyl.io"

LABEL        org.opencontainers.image.source="https://github.com/pterodactyl/yolks"
LABEL        org.opencontainers.image.licenses=MIT

ENV          DEBIAN_FRONTEND noninteractive

RUN          useradd -m -d /home/container -s /bin/bash container

RUN          ln -s /home/container/ /nonexistent

ENV          USER=container HOME=/home/container

## Update base packages
RUN          apt update \
             && apt upgrade -y

## Install dependencies
RUN          apt install -y gcc g++ libgcc1 libc++-dev gdb libc6 git wget curl tar zip unzip binutils xz-utils liblzo2-2 cabextract iproute2 net-tools netcat telnet libatomic1 libsdl1.2debian libsdl2-2.0-0 \
             libfontconfig libicu67 icu-devtools libunwind8 libssl-dev sqlite3 libsqlite3-dev libmariadbclient-dev-compat libduktape205 locales ffmpeg gnupg2 apt-transport-https software-properties-common ca-certificates \
             liblua5.3-0 libz-dev rapidjson-dev tzdata libevent-dev libzip4 libsybdb5 libodbc1 libavahi-compat-libdnssd1 libglib2.0-0

## Configure locale
RUN          update-locale lang=en_US.UTF-8 \
             && dpkg-reconfigure --frontend noninteractive locales

## install libmysqlclient21 for mumble 1.4+
RUN         echo "deb http://ftp.us.debian.org/debian unstable main contrib non-free" >> /etc/apt/sources.list.d/unstable.list \
            apt-get update \
            apt -y install libmysqlclient21 
           
WORKDIR     /home/container

COPY        ./entrypoint.sh /entrypoint.sh
CMD         [ "/bin/bash", "/entrypoint.sh" ]

