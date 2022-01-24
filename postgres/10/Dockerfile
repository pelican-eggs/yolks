# ----------------------------------
# Environment: Postgres DB
# Minimum Panel Version: 0.7.0
# ----------------------------------
FROM postgres:10-alpine

LABEL author="Parker" maintainer="parker@pterodactyl.io"

# UID 999 is the default pterodactyl user
RUN adduser -D -h /home/container container

USER container
ENV HOME /home/container
WORKDIR /home/container

COPY ./entrypoint.sh /entrypoint.sh
CMD ["/bin/bash", "/entrypoint.sh"]
