# -----------------------------------------------------
# MariaDB Image for Pelican
# -----------------------------------------------------
FROM        --platform=$TARGETOS/$TARGETARCH mariadb:11.4

LABEL       author="Michael Parker" maintainer="parker@pelican.dev"

ENV         DEBIAN_FRONTEND=noninteractive

RUN         apt update -y \
            && apt install -y netcat-traditional \
            && useradd -d /home/container -m container -s /bin/bash

USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

COPY        ../entrypoint.sh /entrypoint.sh
CMD ["/bin/bash", "/entrypoint.sh"]
