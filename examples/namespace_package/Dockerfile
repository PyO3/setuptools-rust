FROM quay.io/pypa/manylinux2014_aarch64 AS manylinux

FROM ghcr.io/cross-rs/aarch64-unknown-linux-gnu:edge

RUN curl -L https://github.com/indygreg/python-build-standalone/releases/download/20220318/cpython-3.8.13+20220318-x86_64-unknown-linux-gnu-install_only.tar.gz | tar -xz -C /usr/local

ENV PATH=/usr/local/python/bin:$PATH

COPY --from=manylinux /opt/_internal /opt/_internal
COPY --from=manylinux /opt/python /opt/python
