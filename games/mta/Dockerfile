FROM  --platform=$TARGETOS/$TARGETARCH ubuntu:20.04

ENV   DEBIAN_FRONTEND noninteractive

## add container user
RUN   useradd -m -d /home/container -s /bin/bash container

## update base packages
RUN   apt update \
        &&   apt upgrade -y

## install dependencies
RUN   apt install -y iproute2 tar libssl1.1 curl git default-libmysqlclient-dev libmysqlclient-dev libreadline-gplv2-dev libncurses5-dev libncursesw5-dev \ 
        libtool zip unzip libncurses5 libncursesw5 python3 openssl locales ffmpeg apt-transport-https libc6 binutils xz-utils liblua5.1-0

## configure locale
RUN   update-locale lang=en_US.UTF-8 \
        &&   dpkg-reconfigure --frontend noninteractive locales

WORKDIR /home/container

COPY  ./entrypoint.sh /entrypoint.sh
CMD   [ "/bin/bash", "/entrypoint.sh" ]