# ----------------------------------
# Environment: Postgres DB
# ----------------------------------
FROM --platform=$TARGETOS/$TARGETARCH postgres:18-alpine

LABEL author="Parker" maintainer="parker@pterodactyl.io"

# UID 999 is the default pterodactyl user
RUN adduser -D -h /home/container container

RUN     apk add --no-cache tini curl iproute2 ca-certificates fontconfig git openssl sqlite tar tzdata
USER container
ENV HOME=/home/container
WORKDIR /home/container

STOPSIGNAL SIGINT

COPY        --chown=container:container ../entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT    ["/sbin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
