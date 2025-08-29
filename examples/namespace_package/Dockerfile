FROM quay.io/pypa/manylinux2014_aarch64 AS manylinux

FROM ghcr.io/cross-rs/aarch64-unknown-linux-gnu:edge

# PyO3 needs a host Python interpreter to parse the sysconfigdata of the
# cross-compile interpreter found in /opt/python
RUN apt-get update && apt-get --assume-yes install python3

ENV PATH=/usr/local/python/bin:$PATH

COPY --from=manylinux /opt/_internal /opt/_internal
COPY --from=manylinux /opt/python /opt/python
