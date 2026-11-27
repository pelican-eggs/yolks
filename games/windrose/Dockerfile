# syntax=docker/dockerfile:1
FROM ubuntu:22.04@sha256:b682e31336cc8e0a73ed91ab32b7a95e32591c5ff09994490a20accf9b3600f9 AS python-runtime
ADD --checksum=sha256:7e1adaea26c959d13aa1120be1ae62a1ea1bb52adcb382679fffe9217e22adff https://github.com/astral-sh/python-build-standalone/releases/download/20261124/cpython-3.12.16%2B20261124-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz /tmp/cpython.tar.gz
RUN mkdir -p /opt/windrose-runtime && tar -xzf /tmp/cpython.tar.gz -C /opt/windrose-runtime

FROM ubuntu:22.04@sha256:b682e31336cc8e0a73ed91ab32b7a95e32591c5ff09994490a20accf9b3600f9
LABEL org.opencontainers.image.source="https://github.com/TheIlluminate92/windrose-pelican"
LABEL org.opencontainers.image.description="Pelican runtime tooling; publisher game files are fetched during installation."
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libcurl4 && rm -rf /var/lib/apt/lists/*
COPY --from=python-runtime /opt/windrose-runtime/ /opt/windrose-runtime/
COPY --chmod=0444 native_first_run.py patch_native_world_backup.py install_publisher.py /opt/windrose-first-run/
COPY --chmod=0555 windrose-game /usr/local/bin/windrose-pelican
COPY --chmod=0555 windrose-adapter /usr/local/bin/windrose-adapter
RUN test ! -e /var/tmp/R5 && ln -s /home/container/.windrose-backup-tmp /var/tmp/R5 && mkdir -p /home/container
WORKDIR /home/container
RUN ["/opt/windrose-runtime/python/bin/python3.12", "-E", "-B", "-c", "import fcntl, hashlib, tarfile, zipfile, zlib; assert hasattr(tarfile, 'data_filter')"]
STOPSIGNAL SIGINT
ENTRYPOINT ["/usr/local/bin/windrose-adapter"]
