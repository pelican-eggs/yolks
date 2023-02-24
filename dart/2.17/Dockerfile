FROM        --platform=$TARGETOS/$TARGETARCH dart:2.18.1

LABEL       author="Alden Bansemer" maintainer="alden@knoban.com"

RUN         apt update \
            && apt -y install iproute2 git ca-certificates tzdata \
            && useradd -m -d /home/container container

USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

COPY        ./../entrypoint.sh /entrypoint.sh
CMD         [ "/bin/bash", "/entrypoint.sh" ]
