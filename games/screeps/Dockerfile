FROM alpine:3.15

LABEL author="77wisher77"

EXPOSE 21025

ENV PYTHONUNBUFFERED=1
ENV NVM_DIR=/usr/local/nvm
ENV NODE_VERSION=10.24.1

RUN apk add --no-cache python2 curl bash alpine-sdk linux-headers && \
  python -m ensurepip && \
  rm -r /usr/lib/python*/ensurepip && \
  pip install --upgrade pip setuptools && \
  rm -r /root/.cache && \
  mkdir /usr/local/nvm && \
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash && \
  . $NVM_DIR/nvm.sh && \
  nvm install $NODE_VERSION && \
  nvm alias default $NODE_VERSION && \
  nvm use default && \
  adduser --disabled-password --home /home/container container

USER container
ENV USER=container
ENV HOME=/home/container

ENV SERVER_PORT=21025
ENV SERVER_PASSWORD=
ENV RUNNER_THREADS=1
ENV PROCESSORS_CNT=1

WORKDIR /home/container

COPY ./entrypoint.sh /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]
