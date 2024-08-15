FROM        --platform=$TARGETOS/$TARGETARCH node:20-bookworm-slim

LABEL       author="Michael Parker" maintainer="parker@pterodactyl.io"

# Installiere notwendige Systembibliotheken
RUN         apt update \
            && apt -y install \
            ffmpeg \
            iproute2 \
            git \
            sqlite3 \
            libsqlite3-dev \
            python3 \
            python3-dev \
            ca-certificates \
            dnsutils \
            tzdata \
            zip \
            tar \
            curl \
            build-essential \
            libtool \
            iputils-ping \
            libnss3 \
            libatk-bridge2.0-0 \
            libatk1.0-0 \
            libcups2 \
            libgdk-pixbuf2.0-0 \
            libnspr4 \
            libnss3 \
            libx11-xcb1 \
            libxcomposite1 \
            libxdamage1 \
            libxrandr2 \
            libxss1 \
            libxtst6 \
            libgbm1 \
            libasound2 \
            libpangocairo-1.0-0 \
            libpango-1.0-0 \
            libpangoft2-1.0-0 \
            libgtk-3-0 \
            tini \
            && useradd -m -d /home/container container

# Installiere globale npm-Pakete
RUN         npm install npm@latest typescript ts-node @types/node --location=global

USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

STOPSIGNAL SIGINT

# Kopiere und bereite das Entry-Point-Skript vor
COPY        --chown=container:container ./../entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh

# Setze den Startbefehl
ENTRYPOINT    ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
