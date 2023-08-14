FROM        --platform=$TARGETOS/$TARGETARCH ibm-semeru-runtimes:open-11-jdk

LABEL       author="Michael Parker" maintainer="parker@pterodactyl.io"

RUN         apt update -y \
			&& apt install -y \
					curl \
					lsof \
					ca-certificates \
					openssl \
					git \
					tar \
					sqlite3 \
					fontconfig \
					tzdata \
					iproute2 \
					libfreetype6

## Setup user and working directory
RUN         useradd -m -d /home/container -s /bin/bash container
USER        container
ENV         USER=container HOME=/home/container
WORKDIR     /home/container

COPY        ./../entrypoint.sh /entrypoint.sh
CMD         [ "/bin/bash", "/entrypoint.sh" ]
