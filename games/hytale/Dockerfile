FROM        --platform=$TARGETOS/$TARGETARCH eclipse-temurin:25-jdk-noble

LABEL       author="Michael Parker" maintainer="parker@pelican.dev"
LABEL       author="gOOvER" maintainer="eggs@goover.dev"
LABEL       org.opencontainers.image.source="https://github.com/pelican-eggs/yolks"
LABEL       org.opencontainers.image.licenses=MIT

RUN         apt update -y \
            && apt install -y \
                curl \
                wget \
                lsof \
                ca-certificates \
                openssl \
                git \
                tar \
                sqlite3 \
                fontconfig \
                tzdata \
                iproute2 \
                libfreetype6 \
                tini \
                zip \
                unzip \
                jq \
                dbus \
            && apt clean \
            && rm -rf /var/lib/apt/lists/*


## configure locale
RUN         sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
            locale-gen
ENV         LANG en_US.UTF-8
ENV         LANGUAGE en_US:en
ENV         LC_ALL en_US.UTF-8

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
