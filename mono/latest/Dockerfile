# ----------------------------------
# Mono Latest Image
# Minimum Panel Version: 1.2.x
# ----------------------------------
FROM        ghcr.io/parkervcp/yolks:debian

LABEL       author="Torsten Widmann" maintainer="support@goover.de"

RUN         apt update \
            && apt -y upgrade
RUN         apt install -y fontconfig dirmngr
RUN         apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
RUN         sh -c 'echo "deb https://download.mono-project.com/repo/debian stable-buster main" > /etc/apt/sources.list.d/mono-official-stable.list'
RUN         apt update
RUN         apt install mono-complete -y

USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

COPY        ./entrypoint.sh /entrypoint.sh
CMD         ["/bin/bash", "/entrypoint.sh"]
