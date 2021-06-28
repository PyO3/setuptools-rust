# Setuptools plugin for Rust extensions

![example workflow](https://github.com/PyO3/setuptools-rust/actions/workflows/ci.yml/badge.svg)
[![pypi package](https://badge.fury.io/py/setuptools-rust.svg)](https://badge.fury.io/py/setuptools-rust)
[![readthedocs](https://readthedocs.org/projects/pip/badge/)](https://setuptools-rust.readthedocs.io/en/latest/)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

`setuptools-rust` is a plugin for `setuptools` to build Rust Python extensions implemented with [PyO3](https://github.com/PyO3/pyo3) or [rust-cpython](https://github.com/dgrunwald/rust-cpython).

Compile and distribute Python extensions written in Rust as easily as if
they were written in C.

## Setup

For a complete example, see
[html-py-ever](https://github.com/PyO3/setuptools-rust/tree/main/examples/html-py-ever).

First, you need to create a bunch of files:

### setup.py

```python
from setuptools import setup
from setuptools_rust import Binding, RustExtension

setup(
    name="hello-rust",
    version="1.0",
    rust_extensions=[RustExtension("hello_rust.hello_rust", binding=Binding.PyO3)],
    packages=["hello_rust"],
    # rust extensions are not zip safe, just like C-extensions.
    zip_safe=False,
)
```

For a complete reference of the options supported by the `RustExtension` class, see the
[API reference](https://setuptools-rust.readthedocs.io/en/latest/reference.html).

### MANIFEST.in

This file is required for building source distributions

```text
include Cargo.toml
recursive-include src *
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools", "wheel", "setuptools-rust"]
```

### build-wheels.sh

```bash
#!/bin/bash
set -ex

curl https://sh.rustup.rs -sSf | sh -s -- --default-toolchain stable -y
export PATH="$HOME/.cargo/bin:$PATH"

cd /io

for PYBIN in /opt/python/cp{35,36,37,38,39}*/bin; do
    "${PYBIN}/pip" install -U setuptools wheel setuptools-rust
    "${PYBIN}/python" setup.py bdist_wheel
done

for whl in dist/*.whl; do
    auditwheel repair "$whl" -w dist/
done
```

## Usage

You can use same commands as for c-extensions. For example:

```
>>> python ./setup.py develop
running develop
running egg_info
writing hello-rust.egg-info/PKG-INFO
writing top-level names to hello_rust.egg-info/top_level.txt
writing dependency_links to hello_rust.egg-info/dependency_links.txt
reading manifest file 'hello_rust.egg-info/SOURCES.txt'
writing manifest file 'hello_rust.egg-info/SOURCES.txt'
running build_ext
running build_rust
cargo build --manifest-path extensions/Cargo.toml --features python3
    Finished debug [unoptimized + debuginfo] target(s) in 0.0 secs

Creating /.../lib/python3.6/site-packages/hello_rust.egg-link (link to .)

Installed hello_rust
Processing dependencies for hello_rust==1.0
Finished processing dependencies for hello_rust==1.0
```

Or you can use commands like bdist_wheel (after installing wheel).

By default, `develop` will create a debug build, while `install` will create a release build.

### Binary wheels on linux

To build binary wheels on linux, you need to use the [manylinux docker container](https://github.com/pypa/manylinux). You also need a `build-wheels.sh` similar to [the one in the example](https://github.com/PyO3/setuptools-rust/blob/main/examples/html-py-ever/build-wheels.sh), which will be run in that container.

First, pull the `manylinux2014` Docker image:

```bash
docker pull quay.io/pypa/manylinux2014_x86_64
```

Then use the following command to build wheels for supported Python versions:

```bash
docker run --rm -v `pwd`:/io quay.io/pypa/manylinux2014_x86_64 bash /io/build-wheels.sh
```

This will create wheels in the `dist` directory:

```bash
$ ls dist
hello_rust-0.1.0-cp35-cp35m-linux_x86_64.whl          hello_rust-0.1.0-cp35-cp35m-manylinux2014_x86_64.whl
hello_rust-0.1.0-cp36-cp36m-linux_x86_64.whl          hello_rust-0.1.0-cp36-cp36m-manylinux2014_x86_64.whl
hello_rust-0.1.0-cp37-cp37m-linux_x86_64.whl          hello_rust-0.1.0-cp37-cp37m-manylinux2014_x86_64.whl
hello_rust-0.1.0-cp38-cp38-linux_x86_64.whl           hello_rust-0.1.0-cp38-cp38-manylinux2014_x86_64.whl
hello_rust-0.1.0-cp39-cp39-linux_x86_64.whl           hello_rust-0.1.0-cp39-cp39-manylinux2014_x86_64.whl
```

You can then upload the `manylinux2014` wheels to pypi using [twine](https://github.com/pypa/twine).

It is possible to use any of the `manylinux` docker images: `manylinux1`, `manylinux2010` or `manylinux2014`. (Just replace `manylinux2014` in the above instructions with the alternative version you wish to use.)

### Binary wheels on macOS

For building wheels on macOS it is sufficient to run the `bdist_wheel` command, i.e. `setup.py bdist_wheel`.

To build `universal2` wheels set the `ARCHFLAGS` environment variable to contain both `x86_64` and `arm64`, for example `ARCHFLAGS="-arch x86_64 -arch arm64"`. Wheel-building solutions such as [`cibuildwheel`](https://github.com/joerick/cibuildwheel) set this environment variable automatically.

## Commands

  - `build` - Standard build command will also build all rust extensions.
  - `build_rust` - Command builds all rust extensions.
  - `clean` - Standard clean command executes cargo clean for all rust
    extensions.
  - `tomlgen_rust` - Automatically generate a Cargo.toml manifest based
    on Python package metadata. See the [example
    project](https://github.com/PyO3/setuptools-rust/tree/main/examples/tomlgen)
    on GitHub for more information about this command.
