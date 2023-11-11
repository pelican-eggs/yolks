FROM          --platform=$TARGETOS/$TARGETARCH python:3.11-slim-bookworm

LABEL         author="Michael Parker" maintainer="parker@pterodactyl.io"


RUN           mkdir -p /usr/share/man/man1
RUN           apt update \
              && apt -y upgrade \
              && apt -y install \
                     git \
                     ca-certificates \
                     dnsutils \
                     iproute2 \
                     wget \
                     curl \
                     xz-utils \
                     openjdk-17-jre-headless \
                     zlib1g-dev \
                     libffi-dev \
                     libmagickwand-dev \
                     unzip \
                     libaa1-dev \
                     build-essential \
                     tk-dev \
                     libncurses5-dev \
                     libncursesw5-dev \
                     libreadline6-dev \
                     libdb5.3-dev \
                     libgdbm-dev \
                     libsqlite3-dev \
                     libssl-dev \
                     libbz2-dev \
                     libexpat1-dev \
                     liblzma-dev \
                     ffmpeg \
                     imagemagick \
					 tini

RUN           pip install --upgrade pip
RUN           pip install python-forecastio tweepy unidecode discord-text-sanitizer mcstatus bs4 sqlalchemy geocoder valve python-valve py-cpuinfo psutil

RUN           mkdir -p /home/container/.config/Red-DiscordBot/
RUN           ln -s /home/container/.config/Red-DiscordBot/ /usr/local/share/Red-DiscordBot

## Setup user and working directory
RUN         useradd -m -d /home/container -s /bin/bash container
USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

STOPSIGNAL SIGINT

COPY        --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT    ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
