FROM        --platform=$TARGETOS/$TARGETARCH debian:bullseye-slim

LABEL       author="David Wolfe (Red-Thirten)" maintainer="rehlmgaming@gmail.com"

LABEL       org.opencontainers.image.source="https://github.com/parkervcp/yolks"
LABEL       org.opencontainers.image.licenses=MIT

## Update base packages and install dependencies
ENV         DEBIAN_FRONTEND=noninteractive
RUN         dpkg --add-architecture i386 \
            && apt-get update \
            && apt-get upgrade -y \
            && apt-get install -y \
                curl \
                tzdata \
                locales \
                iproute2 \
                gettext-base \
                ca-certificates \
                numactl \
                libssl-dev \
                lib32gcc-s1 \
                libsdl2-2.0-0 \
                libsdl2-2.0-0:i386 \
                libstdc++6 \
                libstdc++6:i386 \
                lib32stdc++6 \
                libnss-wrapper \
                libnss-wrapper:i386 \
                libtbb2 \
                libtbb2:i386 \
                tini

## Configure locale
RUN         update-locale lang=en_US.UTF-8 \
            && dpkg-reconfigure --frontend noninteractive locales

## Prepare NSS Wrapper for the entrypoint as a workaround for Arma 3 requiring a valid UID
ENV         NSS_WRAPPER_PASSWD=/tmp/passwd NSS_WRAPPER_GROUP=/tmp/group
RUN         touch ${NSS_WRAPPER_PASSWD} ${NSS_WRAPPER_GROUP} \
            && chgrp 0 ${NSS_WRAPPER_PASSWD} ${NSS_WRAPPER_GROUP} \
            && chmod g+rw ${NSS_WRAPPER_PASSWD} ${NSS_WRAPPER_GROUP}
ADD         passwd.template /passwd.template

## Setup user and working directory
RUN         useradd -m -d /home/container -s /bin/bash container
USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

## Copy over entrypoint.sh and set permissions
COPY        --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh

## Start with Tini to pass future stop signals correctly
STOPSIGNAL  SIGINT
ENTRYPOINT  ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
