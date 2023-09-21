FROM        --platform=$TARGETOS/$TARGETARCH debian:bookworm-slim

LABEL       author="QuintenQVD" maintainer="josdekurk@gmail.com"

RUN         apt update \
            && apt -y upgrade
RUN         dpkg --add-architecture i386 \
            && apt update \
            && apt upgrade -y \
            && apt install -y libstdc++6 lib32stdc++6 tar curl iproute2 openssl fontconfig dirmngr ca-certificates dnsutils tzdata zip  \
            && apt install -y libtbb-dev:i386 libtbb-dev:i386 libicu-dev:i386 libtbbmalloc2:i386  \
            && useradd -d /home/container -m container

RUN         mkdir -p /run/systemd && echo 'docker' > /run/systemd/container
RUN         rm -rf /var/lib/apt/lists/*

USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

COPY        ./entrypoint.sh /entrypoint.sh
CMD         [ "/bin/bash", "/entrypoint.sh" ]
