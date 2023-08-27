FROM   --platform=$TARGETOS/$TARGETARCH oven/bun:latest

LABEL author="MrAtox" maintainer="mratox@protonmail.com"

RUN  apt update \
            && apt -y install ffmpeg iproute2 git sqlite3 libsqlite3-dev python3 python3-dev ca-certificates dnsutils tzdata zip tar curl build-essential libtool \
            && useradd -m -d /home/container container

RUN bun upgrade

USER container
ENV USER=container HOME=/home/container
WORKDIR /home/container

ENTRYPOINT []
COPY        ./../entrypoint.sh /entrypoint.sh
CMD          [ "/bin/bash", "/entrypoint.sh" ]
