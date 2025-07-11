FROM --platform=$TARGETOS/$TARGETARCH debian:bookworm-slim

RUN apt update && \
    apt upgrade -y && \
    apt install -y \
        tini \
        wget \
        libsdl1.2debian \
        libsdl2-2.0-0 

RUN wget https://snapshot.debian.org/archive/debian/20190501T215844Z/pool/main/g/glibc/multiarch-support_2.28-10_amd64.deb && \
    wget https://snapshot.debian.org/archive/debian/20141009T042436Z/pool/main/libj/libjpeg8/libjpeg8_8d1-2_amd64.deb && \
    wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.0g-2ubuntu4_amd64.deb && \
    apt install -y ./libjpeg8_8d1-2_amd64.deb ./multiarch-support_2.28-10_amd64.deb ./libssl1.1_1.1.0g-2ubuntu4_amd64.deb

## add container user
RUN   useradd -m -d /home/container -s /bin/bash container

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