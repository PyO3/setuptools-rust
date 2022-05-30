# Setuptools plugin for Rust extensions

[![github actions](https://github.com/PyO3/setuptools-rust/actions/workflows/ci.yml/badge.svg)](https://github.com/PyO3/setuptools-rust/actions/workflows/ci.yml)
[![pypi package](https://badge.fury.io/py/setuptools-rust.svg)](https://pypi.org/project/setuptools-rust/)
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

### pyproject.toml

```toml
[build-system]
requires = ["setuptools", "wheel", "setuptools-rust"]
```

### MANIFEST.in

This file is required for building source distributions

```text
include Cargo.toml
recursive-include src *
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

Or you can use commands like `bdist_wheel` (after installing `wheel`). See also [the notes in the documentation about building wheels](https://setuptools-rust.readthedocs.io/en/latest/building_wheels.html).

Cross-compiling is also supported, using one of [`crossenv`](https://github.com/benfogle/crossenv), [`cross`](https://github.com/rust-embedded/cross) or [`cargo-zigbuild`](https://github.com/messense/cargo-zigbuild).
For examples see the `test-crossenv` and `test-cross` and `test-zigbuild` Github actions jobs in [`ci.yml`](https://github.com/PyO3/setuptools-rust/blob/main/.github/workflows/ci.yml).

By default, `develop` will create a debug build, while `install` will create a release build.

## Commands

  - `build` - Standard build command will also build all rust extensions.
  - `build_rust` - Command builds all rust extensions.
  - `clean` - Standard clean command executes cargo clean for all rust
    extensions.
