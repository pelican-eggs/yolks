FROM        ghcr.io/pelican-eggs/yolks:wine_11

LABEL       org.opencontainers.image.authors="Eric <DasEric@users.noreply.github.com>" \
            org.opencontainers.image.source="https://github.com/pelican-eggs/yolks" \
            org.opencontainers.image.licenses=MIT

USER        root

RUN         apt update \
            && apt install -y --no-install-recommends \
                dbus-x11 \
                firefox-esr \
                fonts-dejavu-core \
                libarchive-tools \
                netcat-openbsd \
                novnc \
                p7zip-full \
                procps \
                socat \
                sysstat \
                tigervnc-standalone-server \
                tigervnc-tools \
                websockify \
                x11-utils \
                xdg-user-dirs \
                xfonts-base \
                xterm \
                exo-utils \
                thunar \
                xfce4-appfinder \
                xfce4-panel \
                xfce4-session \
                xfce4-settings \
                xfce4-terminal \
                xfdesktop4 \
                xfwm4 \
            && update-alternatives --set x-terminal-emulator /usr/bin/xterm \
            && apt clean \
            && rm -rf /var/lib/apt/lists/*

COPY        entrypoint.py fs25ctl.py /opt/fs25/
RUN         chmod 0555 /opt/fs25/entrypoint.py /opt/fs25/fs25ctl.py

ENV         HOME=/home/container \
            USER=container \
            LOGNAME=container \
            SHELL=/bin/bash \
            WINEPREFIX=/home/container/.fs25server \
            WINEARCH=win64 \
            WINEDEBUG=-all \
            DISPLAY=:0 \
            XDG_RUNTIME_DIR=/tmp/xdg-runtime-fs25

USER        container
WORKDIR     /home/container

STOPSIGNAL  SIGINT

CMD         ["/opt/fs25/entrypoint.py"]
