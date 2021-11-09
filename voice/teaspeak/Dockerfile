#
# Copyright (c) 2021 Torsten Widmann
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

FROM      --platform=$BUILDPLATFORM debian:stable-slim

LABEL     author="Torsten Widmann" maintainer="info@goover.de"

LABEL     org.opencontainers.image.source="https://github.com/pterodactyl/yolks"
LABEL     org.opencontainers.image.licenses=MIT

ENV       DEBIAN_FRONTEND=noninteractive

##    update base packages
RUN       apt update \
          &&   apt upgrade -y

##    install dependencies
RUN   apt install -y ffmpeg curl python3 iproute2 libjemalloc2

# Install latest youtube-dl
RUN   curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl
RUN   chmod a+rx /usr/local/bin/youtube-dl

RUN   update-alternatives --install  /usr/bin/python python /usr/bin/python3 1000

RUN   useradd -m -d /home/container container

USER   container
ENV    USER=container HOME=/home/container
WORKDIR /home/container

COPY  ./entrypoint.sh /entrypoint.sh
CMD   ["/bin/bash", "/entrypoint.sh"]
