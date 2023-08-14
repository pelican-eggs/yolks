FROM        --platform=$TARGETOS/$TARGETARCH ibm-semeru-runtimes:open-8-jdk

LABEL       author="Michael Parker" maintainer="parker@pterodactyl.io"

RUN         apt update -y \
						&& apt install -y curl lsof ca-certificates openssl git tar sqlite3 fontconfig tzdata iproute2 libfreetype6 \
						&& useradd -d /home/container -m container

USER        container
ENV         USER=container HOME=/home/container

WORKDIR     /home/container

COPY        ./entrypoint.sh /entrypoint.sh

RUN         chmod +x /entrypoint.sh
CMD         ["/bin/bash", "/entrypoint.sh"]
