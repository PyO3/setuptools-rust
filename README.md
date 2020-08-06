# Setuptools plugin for Rust extensions

[![Build Status](https://travis-ci.org/PyO3/setuptools-rust.svg?branch=master)](https://travis-ci.org/PyO3/setuptools-rust)
[![pypi package](https://badge.fury.io/py/setuptools-rust.svg)](https://badge.fury.io/py/setuptools-rust)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

Note: You might want to check out [maturin](https://github.com/PyO3/maturin), which allows to develop, build and upload without any configuration, though it can't do some things setuptools-rust can, e.g. mixing python and rust in single wheel.

Setuptools helpers for rust Python extensions implemented with [PyO3](https://github.com/PyO3/pyo3) and [rust-cpython](https://github.com/dgrunwald/rust-cpython).

Compile and distribute Python extensions written in rust as easily as if
they were written in C.

## Setup

For a complete example, see
[html-py-ever](https://github.com/PyO3/setuptools-rust/tree/master/html-py-ever).

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

To build binary wheels on linux, you need to use the [manylinux docker container](https://github.com/pypa/manylinux). You also need a `build-wheels.sh` similar to [the one in the example](https://github.com/PyO3/setuptools-rust/blob/master/html-py-ever/build-wheels.sh), which will be run in that container.

First, pull the `manylinux2014` Docker image:

```bash
docker pull quay.io/pypa/manylinux2014_x86_64
```

Then use the following command to build wheels for supported Python versions:

```bash
docker run --rm -v `pwd`:/io quay.io/pypa/manylinux2014_x86_64 /io/build-wheels.sh
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

## RustExtension

You can define rust extension with RustExtension class:

RustExtension(name, path, args=None, features=None,
rust\_version=None, quiet=False, debug=False)

The class for creating rust extensions.

   - param str name
     the full name of the extension, including any packages -- ie.
     *not* a filename or pathname, but Python dotted name. It is
     possible to specify multiple binaries, if extension uses
     Binsing.Exec binding mode. In that case first argument has to be
     dictionary. Keys of the dictionary corresponds to compiled rust
     binaries and values are full name of the executable inside python
     package.

   - param str path
     path to the Cargo.toml manifest file

   - param \[str\] args
     a list of extra argumenents to be passed to cargo.

   - param \[str\] features
     a list of features to also build

   - param \[str\] rustc\_flags
     A list of arguments to pass to rustc, e.g. cargo rustc --features
     \<features\> \<args\> -- \<rustc\_flags\>

   - param str rust\_version
     sematic version of rust compiler version -- for example
     *\>1.14,\<1.16*, default is None

   - param bool quiet
     Does not echo cargo's output. default is False

   - param bool debug
     Controls whether --debug or --release is passed to cargo. If set
     to None then build type is auto-detect. Inplace build is debug
     build otherwise release. Default: None

   - param int binding
     Controls which python binding is in use. Binding.PyO3 uses PyO3
     Binding.RustCPython uses rust-cpython Binding.NoBinding uses no
     binding. Binding.Exec build executable.

   - param int strip
     Strip symbols from final file. Does nothing for debug build.
     Strip.No - do not strip symbols (default) Strip.Debug - strip
     debug symbols Strip.All - strip all symbols

   - param bool script
     Generate console script for executable if Binding.Exec is used.

   - param bool native
     Build extension or executable with "-C target-cpu=native"

   - param bool optional
     if it is true, a build failure in the extension will not abort the
     build process, but instead simply not install the failing
     extension.

## Commands

  - build - Standard build command builds all rust extensions.
  - build\_rust - Command builds all rust extensions.
  - clean - Standard clean command executes cargo clean for all rust
    extensions.
  - check - Standard check command executes cargo check for all rust
    extensions.
  - tomlgen\_rust - Automatically generate a Cargo.toml manifest based
    on Python package metadata. See the [example
    project](https://github.com/PyO3/setuptools-rust/tree/master/example_tomlgen)
    on GitHub for more information about this command.
