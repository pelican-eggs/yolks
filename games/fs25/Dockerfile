# syntax=docker/dockerfile:1

# Compile against the same Debian libraries used by the runtime image.
# A separate prefix keeps WineHQ 11 available as a compatibility option.
FROM        ghcr.io/pelican-eggs/yolks:wine_11 AS wine-build

USER        root
ARG         WINE_BUILD_JOBS=2
ADD         --checksum=sha256:a07652adb965e657837e8013ecb525303fc733555c78a5295a63d48b0ca9a120 \
            https://codeload.github.com/ValveSoftware/wine/tar.gz/dc26e61847081a1b5cb0733dc30feba6ee575482 \
            /opt/fs25/wine-source/valve-wine.tar.gz

RUN         apt update \
            && apt install -y --no-install-recommends \
                build-essential mingw-w64 \
                autoconf bison flex pkg-config \
                libasound2-dev libavcodec-dev libavformat-dev libavutil-dev \
                libcups2-dev libdbus-1-dev libegl-dev \
                libfontconfig1-dev libfreetype-dev libgl-dev libgnutls28-dev \
                libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
                libkrb5-dev libpcap-dev libpulse-dev libsdl2-dev \
                libudev-dev libusb-1.0-0-dev libvulkan-dev \
                libx11-dev libxcomposite-dev libxcursor-dev libxext-dev \
                libxfixes-dev libxi-dev libxinerama-dev libxrandr-dev libxrender-dev \
            && mkdir -p /tmp/wine-source /tmp/wine-build \
            && tar -xzf /opt/fs25/wine-source/valve-wine.tar.gz -C /tmp/wine-source --strip-components=1 \
            && cp /tmp/wine-source/COPYING.LIB /tmp/wine-source/LICENSE /tmp/wine-source/AUTHORS /opt/fs25/wine-source/ \
            && printf 'Wine version 11.0-fs25-proton-dc26e61\n' > /tmp/wine-source/VERSION \
            && cp /tmp/wine-source/VERSION /opt/fs25/wine-source/VERSION.fs25 \
            && chmod 0444 /opt/fs25/wine-source/* \
            && cd /tmp/wine-source && autoreconf -f \
            && cd /tmp/wine-build \
            && CFLAGS='-O2 -march=x86-64' /tmp/wine-source/configure \
                --prefix=/opt/fs25/wine --enable-archs=i386,x86_64 --with-mingw=yes --disable-tests --without-wayland \
            && make -j"${WINE_BUILD_JOBS}" \
            && make install

FROM        ghcr.io/pelican-eggs/yolks:wine_11

LABEL       org.opencontainers.image.authors="Eric <DasEric@users.noreply.github.com>" \
            org.opencontainers.image.source="https://github.com/pelican-eggs/yolks" \
            org.opencontainers.image.licenses="MIT AND LGPL-2.1-or-later"

USER        root

# Let Debian select its FFmpeg library ABI instead of pinning release-specific package names.
RUN         apt update \
            && apt install -y --no-install-recommends \
                dbus-x11 \
                ffmpeg \
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

COPY        --from=wine-build /opt/fs25/wine /opt/fs25/wine
COPY        --from=wine-build /opt/fs25/wine-source /opt/fs25/wine-source
RUN         ldd /opt/fs25/wine/bin/wine /opt/fs25/wine/bin/wineserver > /tmp/fs25-wine-libs.txt \
            && find /opt/fs25/wine/lib/wine/x86_64-unix -type f -name '*.so' \
                -exec env LD_LIBRARY_PATH=/opt/fs25/wine/lib/wine/x86_64-unix ldd {} \; >> /tmp/fs25-wine-libs.txt \
            && cat /tmp/fs25-wine-libs.txt \
            && ! grep -q 'not found' /tmp/fs25-wine-libs.txt \
            && rm /tmp/fs25-wine-libs.txt
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

# Verify both Windows architectures against the final runtime, without touching server data.
RUN         WINEPREFIX=/tmp/fs25-wine-smoke WINEDEBUG=-all \
            WINEFSYNC=0 PROTON_NO_NTSYNC=1 WINESERVER=/opt/fs25/wine/bin/wineserver \
            PATH=/opt/fs25/wine/bin:$PATH \
            timeout 240 xvfb-run -a /bin/sh -c \
                'wineboot --init && wine cmd /d /s /c ver && wine "C:\windows\syswow64\cmd.exe" /d /s /c ver && wineserver -w' \
            && rm -rf /tmp/fs25-wine-smoke

STOPSIGNAL  SIGINT

CMD         ["/opt/fs25/entrypoint.py"]
