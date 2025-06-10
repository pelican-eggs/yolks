FROM        --platform=$TARGETOS/$TARGETARCH ubuntu:24.04

LABEL       org.opencontainers.image.source="https://github.com/pelican-eggs/yolks"
LABEL       org.opencontainers.image.licenses=AGPL-3.0-or-later

ENV         DEBIAN_FRONTEND=noninteractive

RUN         dpkg --add-architecture i386 \
			&& apt update \
			&& apt upgrade -y \
			&& apt -y install tar curl gcc g++ lib32gcc-s1 libgcc-10-dev libcurl4-gnutls-dev:i386 libssl-dev:i386 libssl-dev libcurl4t64:i386 lib32stdc++6 libcurl3t64-gnutls:i386 libsdl2-2.0-0:i386 iproute2 gdb libsdl1.2debian telnet net-tools netcat tzdata libtinfo6:i386 libcurl4-gnutls-dev:i386 libncurses6:i386 libcurl4-gnutls:i386 faketime:i386 \
			&& apt -y install lib32tinfo6 lib32z1 libtbb12 libtinfo6 libstdc++6 readline-common libncursesw6 libfontconfig1 libnss-wrapper gettext-base libc6-i386 libcurl4t64 libssl3t64 libssl3t64:i386 libc6 libc6:i386 xvfb gdb libc++-dev tini 

RUN 		useradd -d /home/container -m container

## Specific to pavlov_vr
RUN			rm /usr/lib/x86_64-linux-gnu/libc++.so  \
			&& ln -s /usr/lib/x86_64-linux-gnu/libc++.so.1 /usr/lib/x86_64-linux-gnu/libc++.so

## install rcon
RUN         cd /tmp/ \
            && curl -sSL https://github.com/gorcon/rcon-cli/releases/download/v0.10.3/rcon-0.10.3-amd64_linux.tar.gz > rcon.tar.gz \
            && tar xvf rcon.tar.gz \
            && mv rcon-0.10.3-amd64_linux/rcon /usr/local/bin/

USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

STOPSIGNAL SIGINT

COPY        --chown=container:container ../entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT    ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
