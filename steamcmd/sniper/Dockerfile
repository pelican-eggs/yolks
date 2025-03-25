# ---------------------------------------------
# Steam Sniper image (RT3)
# ---------------------------------------------
FROM         --platform=$TARGETOS/$TARGETARCH registry.gitlab.steamos.cloud/steamrt/sniper/platform:latest-container-runtime-depot

LABEL       author="Alexander Ballauf" maintainer="admin@ballaual.de"
LABEL       org.opencontainers.image.description SteamRT3 Platform image for Pterodactyl Source engine servers. 

# Install required packages
RUN         dpkg --add-architecture i386 \
            && apt update \
            && apt upgrade -y \
            && apt install -y \
                tar \
                curl \
                gcc \
                g++ \
                lib32gcc-s1 \
                libgcc1 \
                libcurl4-gnutls-dev:i386 \
                libssl1.1:i386 \
                libcurl4:i386 \
                lib32tinfo6 \
                libtinfo6:i386 \
                lib32z1 \
                lib32stdc++6 \
                libncurses5:i386 \
                libcurl3-gnutls:i386 \
                libsdl2-2.0-0:i386 \
                libsdl2-2.0-0 \
                iproute2 \
                gdb \
                libsdl1.2debian \
                libfontconfig1 \
                telnet \
                net-tools \
                netcat \
                tzdata \
                xvfb \
                tini \
                libc6

# Install rcon
RUN         cd /tmp/ \
            && curl -sSL https://github.com/gorcon/rcon-cli/releases/download/v0.10.3/rcon-0.10.3-amd64_linux.tar.gz > rcon.tar.gz \
            && tar xvf rcon.tar.gz \
            && mv rcon-0.10.3-amd64_linux/rcon /usr/local/bin/
            
# Setup user and working directory
RUN         useradd -m -d /home/container -s /bin/bash container
USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

STOPSIGNAL  SIGINT

COPY        --chown=container:container ./../entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT  ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]