FROM        --platform=$TARGETOS/$TARGETARCH debian:bullseye-slim

LABEL       org.opencontainers.image.authors="i2007@damw.eu"
LABEL       version="1.0"

ENV         DEBIAN_FRONTEND noninteractive

# Install Dependencies
RUN         apt update \
            && apt upgrade -y \
            && apt install -y ca-certificates less locales pulseaudio python python3 sudo x11vnc x11-xkb-utils xvfb iproute2 ffmpeg curl liblcms2-2 libatomic1 libxcb-xinerama0 fontconfig \
			libasound2 libegl1-mesa libglib2.0-0 libnss3 libpci3 libpulse0 libxcursor1 libxslt1.1 libx11-xcb1 libxkbcommon0 bzip2 libxss1 libxcomposite1 libevent-2.1-7 libxcb-icccm4 \
   			libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0 tini \
            && useradd -m -d /home/container container


ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

STOPSIGNAL SIGINT

COPY        --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT    ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]