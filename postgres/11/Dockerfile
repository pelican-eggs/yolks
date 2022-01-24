# ----------------------------------
# Environment: Postgres DB
# -----------------------------------
FROM --platform=$TARGETOS/$TARGETARCH postgres:11-alpine

LABEL author="Parker" maintainer="parker@pterodactyl.io"

# UID 999 is the default pterodactyl user
RUN adduser -D -h /home/container container

USER container
ENV HOME /home/container
WORKDIR /home/container

COPY ./entrypoint.sh /entrypoint.sh
CMD ["/bin/bash", "/entrypoint.sh"]
