#!/bin/bash
set -ex

curl https://sh.rustup.rs -sSf | sh -s -- --default-toolchain nightly -y
export PATH="$HOME/.cargo/bin:$PATH"

cd /io

for PYBIN in /opt/python/{cp27-cp27m,cp27-cp27mu,cp35-cp35m,cp36-cp36m,cp37-cp37m}/bin; do
    export PYTHON_SYS_EXECUTABLE="$PYBIN/python"

    "${PYBIN}/pip" install -U setuptools wheel setuptools-rust
    "${PYBIN}/python" setup.py bdist_wheel
done

for whl in dist/*.whl; do
    auditwheel repair "$whl" -w dist/
done
