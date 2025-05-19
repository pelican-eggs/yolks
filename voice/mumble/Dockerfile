FROM --platform=$TARGETOS/$TARGETARCH ghcr.io/mumble-voip/mumble-server:latest

# Install runtime dependencies
RUN apt update \
    && apt -y install iproute2 tini \
    && useradd -m -d /home/container container

# Set up user and working directory
USER container
ENV USER=container HOME=/home/container
WORKDIR /home/container

# Set the stop signal
STOPSIGNAL SIGINT

# Copy and set up the entrypoint script
COPY --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Define entrypoint and command
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["/entrypoint.sh"]