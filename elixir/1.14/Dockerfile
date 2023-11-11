FROM --platform=$TARGETOS/$TARGETARCH elixir:1.14.5-slim

LABEL author="MrAvox" maintainer="mravox@proton.me"

RUN  apt update \
            && apt -y install git dnsutils curl iproute2 ffmpeg \
            && useradd -m -d /home/container container

USER container
ENV USER=container HOME=/home/container
WORKDIR /home/container

ENTRYPOINT []
COPY ./../entrypoint.sh /entrypoint.sh
CMD [ "/bin/bash", "/entrypoint.sh" ]
