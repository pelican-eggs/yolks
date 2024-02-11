## use latest build at base that still has wine 8 (8.0.2)
FROM            ghcr.io/parkervcp/yolks:wine_latest@sha256:db82ec2e67fe90d7d66500c3de64a079051a34ad7d2a5ed480c8c72117f9af04

## install required packages but hold all wine packages
RUN             dpkg --add-architecture i386 \
                && apt-mark hold winehq-stable \
                && apt-mark hold wine-stable-amd64 \
                && apt-mark hold wine-stable \
                && apt update -y \
				&& apt upgrade -y \
                && rm /usr/sbin/winetricks /entrypoint.sh

## Install rcon in it as this was added later then the base image release
RUN             cd /tmp/ \
                && curl -sSL https://github.com/gorcon/rcon-cli/releases/download/v0.10.3/rcon-0.10.3-amd64_linux.tar.gz > rcon.tar.gz \
                && tar xvf rcon.tar.gz \
                && mv rcon-0.10.3-amd64_linux/rcon /usr/local/bin/


# Update the Winetricks version
RUN	            wget -q -O /usr/sbin/winetricks https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks \
                && chmod +x /usr/sbin/winetricks

ENV             HOME=/home/container
ENV             WINEPREFIX=/home/container/.wine
ENV             WINEDLLOVERRIDES="mscoree,mshtml="
ENV             DISPLAY=:0
ENV             DISPLAY_WIDTH=1024
ENV             DISPLAY_HEIGHT=768
ENV             DISPLAY_DEPTH=16
ENV             AUTO_UPDATE=1
ENV             XVFB=1

COPY            ./../entrypoint.sh /entrypoint.sh
CMD             [ "/bin/bash", "/entrypoint.sh" ]
