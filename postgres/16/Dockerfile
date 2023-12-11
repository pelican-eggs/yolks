# ----------------------------------
# Environment: Postgres DB
# ----------------------------------
FROM --platform=$TARGETOS/$TARGETARCH postgres:16-bookworm

LABEL author="Parker" maintainer="parker@pterodactyl.io"

# UID 999 is the default pterodactyl user
RUN adduser -D --home /home/container container

RUN apt install tini curl iproute2 ca-certificates fontconfig git openssl sqlite tar tzdata

# Remove cached packages
RUN apt clean

USER container
ENV HOME /home/container
WORKDIR /home/container

STOPSIGNAL SIGINT

COPY          --chown=container:container ../entrypoint.sh /entrypoint.sh
RUN           chmod +x /entrypoint.sh
ENTRYPOINT    ["/sbin/tini", "-g", "--"]
CMD           ["/entrypoint.sh"]
