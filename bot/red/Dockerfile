FROM        --platform=$TARGETOS/$TARGETARCH python:3.10-slim

LABEL       author="Michael Parker" maintainer="parker@pterodactyl.io"

RUN         mkdir -p /usr/share/man/man1 \
            && apt update \
            && apt -y install git ca-certificates dnsutils iproute2 wget curl xz-utils git openjdk-11-jre \
            zlib1g-dev libffi-dev git libmagickwand-dev unzip libaa1-dev build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev ffmpeg imagemagick \
            && pip install python-forecastio tweepy unidecode discord-text-sanitizer mcstatus bs4 sqlalchemy geocoder valve python-valve py-cpuinfo psutil \
            && useradd -m -d /home/container container \
            && mkdir -p /home/container/.config/Red-DiscordBot/ \
            && ln -s /home/container/.config/Red-DiscordBot/ /usr/local/share/Red-DiscordBot

USER        container
ENV         USER=container HOME=/home/container 
WORKDIR     /home/container

COPY        ./entrypoint.sh /entrypoint.sh
CMD         ["/bin/bash", "/entrypoint.sh"]
