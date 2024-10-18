FROM quay.io/pypa/manylinux2014_aarch64 AS manylinux

FROM ghcr.io/cross-rs/aarch64-unknown-linux-gnu:edge

ARG STANDALONE_PYTHON_RELEASE
ARG STANDALONE_PYTHON_VERSION

RUN test -n "$STANDALONE_PYTHON_RELEASE" || (echo "STANDALONE_PYTHON_RELEASE not set" && false)
RUN test -n "$STANDALONE_PYTHON_VERSION" || (echo "STANDALONE_PYTHON_VERSION not set" && false)

RUN curl -L https://github.com/indygreg/python-build-standalone/releases/download/${STANDALONE_PYTHON_RELEASE}/cpython-${STANDALONE_PYTHON_VERSION}+${STANDALONE_PYTHON_RELEASE}-x86_64-unknown-linux-gnu-install_only.tar.gz | tar -xz -C /usr/local

ENV PATH=/usr/local/python/bin:$PATH

COPY --from=manylinux /opt/_internal /opt/_internal
COPY --from=manylinux /opt/python /opt/python
