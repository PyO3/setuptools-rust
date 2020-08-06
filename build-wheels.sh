#!/bin/bash
set -e -x

mkdir ~/rust-installer
curl -sL https://static.rust-lang.org/rustup.sh -o ~/rust-installer/rustup.sh
sh ~/rust-installer/rustup.sh --prefix=~/rust --spec=stable -y --disable-sudo
export PATH="$HOME/rust/bin:$PATH"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$HOME/rust/lib"

# Compile wheels
for PYBIN in /opt/python/cp{35,36,37,38,39}*/bin; do
    rm -f /io/build/lib.*
    "${PYBIN}/pip" install -U  setuptools setuptools-rust wheel
    "${PYBIN}/pip" wheel /io/ -w /io/dist/
done

# Bundle external shared libraries into the wheels
for whl in /io/dist/*.whl; do
    auditwheel repair "$whl" -w /io/dist/
done

# Install packages and test
for PYBIN in /opt/python/cp{35,36,37,38,39}*/bin; do
    "${PYBIN}/pip" install hello-rust --no-index -f /io/dist/
done
