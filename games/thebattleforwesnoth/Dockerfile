FROM        --platform=$TARGETOS/$TARGETARCH debian:bookworm-slim

LABEL author="Michael Parker" maintainer="parker@pterodactyl.io"

## update base packages
RUN apt update && apt upgrade -y

## install dependencies
RUN   apt install -y gcc g++ libgcc1 libc++-dev gdb libc6 git tar zip unzip libssl-dev tini iproute2 \ 
      libboost-filesystem-dev libboost-iostreams-dev libboost-locale-dev libboost-random-dev libboost-regex-dev libboost-program-options-dev libboost-system-dev libboost-coroutine-dev libboost-graph-dev \
      libsdl2-dev libcurl4-openssl-dev libcairo2-dev libvorbis-dev libbz2-dev zlib1g-dev libssl-dev libcrypto++-dev openssl cmake libsdl2-image-dev libsdl2-mixer-dev libsdl-pango-dev


## add container user
RUN   useradd -m -d /home/container -s /bin/bash container
USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

STOPSIGNAL SIGINT

COPY        --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT    ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
