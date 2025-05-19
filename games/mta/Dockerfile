FROM  --platform=$TARGETOS/$TARGETARCH ubuntu:20.04
ENV   DEBIAN_FRONTEND=noninteractive

## update base packages
RUN   apt update && \
      apt upgrade -y

## install dependencies
RUN   apt install -y \
        tini \
        iproute2 \
        curl \
        git \
        zip \
        unzip \
        tar \
        xz-utils \
        apt-transport-https \
        openssl \
        default-libmysqlclient-dev \
        libreadline-dev \
        libncurses-dev \
        libtool \
        python3  \
        locales \
        ffmpeg \
        libc6 \
        binutils  \
        liblua5.1-0

## configure locale
RUN   update-locale lang=en_US.UTF-8 && \
      dpkg-reconfigure --frontend noninteractive locales

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