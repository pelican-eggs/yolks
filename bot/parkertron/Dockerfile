FROM    --platform=$TARGETOS/$TARGETARCH debian:bullseye

LABEL   author="Michael Parker" maintainer="parker@pterodactyl.io"

ENV     DEBIAN_FRONTEND noninteractive

RUN     apt update -y \
        # general packages
     && apt install -y iproute2 ca-certificates \
        # additional packages for tesseract and eng lang support
        libtesseract-dev tesseract-ocr-eng \
        # add container user to run application
     && useradd -m -d /home/container container

USER    container
ENV     USER=container HOME=/home/container
WORKDIR /home/container

COPY    ./entrypoint.sh /entrypoint.sh
CMD     ["/bin/bash", "/entrypoint.sh"]
