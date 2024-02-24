# Setuptools plugin for Rust extensions

[![github actions](https://github.com/PyO3/setuptools-rust/actions/workflows/ci.yml/badge.svg)](https://github.com/PyO3/setuptools-rust/actions/workflows/ci.yml)
[![pypi package](https://badge.fury.io/py/setuptools-rust.svg)](https://pypi.org/project/setuptools-rust/)
[![readthedocs](https://readthedocs.org/projects/pip/badge/)](https://setuptools-rust.readthedocs.io/en/latest/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

`setuptools-rust` is a plugin for `setuptools` to build Rust Python extensions implemented with [PyO3](https://github.com/PyO3/pyo3) or [rust-cpython](https://github.com/dgrunwald/rust-cpython).

Compile and distribute Python extensions written in Rust as easily as if
they were written in C.

## Quickstart

The following is a very basic tutorial that shows how to use `setuptools-rust` in `pyproject.toml`.
It assumes that you already have a bunch of Python and Rust files that you want
to distribute. You can see examples for these files in the
[`examples/hello-world`](https://github.com/PyO3/setuptools-rust/tree/main/examples/hello-world)
directory in the [github repository](https://github.com/PyO3/setuptools-rust).
The [PyO3 docs](https://pyo3.rs) have detailed information on how to write Python
modules in Rust.

```
hello-world
├── python
│   └── hello_world
│       └── __init__.py
└── rust
    └── lib.rs
```

Once the implementation files are in place, we need to add a `pyproject.toml`
file that tells anyone that wants to use your project how to build it.
In this file, we use an [array of tables](https://toml.io/en/v1.0.0#array-of-tables)
(TOML jargon equivalent to Python's list of dicts) for ``[[tool.setuptools-rust.ext-modules]]``,
to specify different extension modules written in Rust:


```toml
# pyproject.toml
[build-system]
requires = ["setuptools", "setuptools-rust"]
build-backend = "setuptools.build_meta"

[project]
name = "hello-world"
version = "1.0"

[tool.setuptools.packages]
# Pure Python packages/modules
find = { where = ["python"] }

[[tool.setuptools-rust.ext-modules]]
# Private Rust extension module to be nested into the Python package
target = "hello_world._lib"  # The last part of the name (e.g. "_lib") has to match lib.name in Cargo.toml,
                             # but you can add a prefix to nest it inside of a Python package.
path = "Cargo.toml"      # Default value, can be omitted
binding = "PyO3"         # Default value, can be omitted
```

Each extension module should map directly into the corresponding `[lib]` table on the
[Cargo manifest file](https://doc.rust-lang.org/cargo/reference/manifest.html):

```toml
# Cargo.toml
[package]
name = "hello-world"
version = "0.1.0"
edition = "2021"

[dependencies]
pyo3 = "0.20.3"

[lib]
name = "_lib"  # private module to be nested into Python package,
               # needs to match the name of the function with the `[#pymodule]` attribute
path = "rust/lib.rs"
crate-type = ["cdylib"]  # required for shared library for Python to import from.

# See more keys and their definitions at https://doc.rust-lang.org/cargo/reference/manifest.html
# See also PyO3 docs on writing Cargo.toml files at https://pyo3.rs
```

You will also need to tell Setuptools that the Rust files are required to build your
project from the [source distribution](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html).
That can be done either via `MANIFEST.in` (see example below) or via a plugin like
[`setuptools-scm`](https://pypi.org/project/setuptools-scm/).

```
# MANIFEST.in
include Cargo.toml
recursive-include rust *.rs
```

With these files in place, you can install the project in a virtual environment
for testing and making sure everything is working correctly:

```powershell
# cd hello-world
python3 -m venv .venv
source .venv/bin/activate  # on Linux or macOS
.venv\Scripts\activate     # on Windows
python -m pip install -e .
python
>>> import hello_world
# ... try running something from your new extension module ...
# ... better write some tests with pytest ...
```

## Next steps and final remarks

- When you are ready to distribute your project, have a look on
  [the notes in the documentation about building wheels](https://setuptools-rust.readthedocs.io/en/latest/building_wheels.html).

- Cross-compiling is also supported, using one of
  [`crossenv`](https://github.com/benfogle/crossenv),
  [`cross`](https://github.com/rust-embedded/cross) or
  [`cargo-zigbuild`](https://github.com/messense/cargo-zigbuild).
  For examples see the `test-crossenv` and `test-cross` and `test-zigbuild` Github actions jobs in
  [`ci.yml`](https://github.com/PyO3/setuptools-rust/blob/main/.github/workflows/ci.yml).

- You can also use `[[tool.setuptools-rust.bins]]` (instead of `[[tool.setuptools-rust.ext-modules]]`),
  if you want to distribute a binary executable written in Rust (instead of a library that can be imported by the Python runtime).
  Note however that distributing both library and executable (or multiple executables),
  may significantly increase the size of the
  [wheel](https://packaging.python.org/en/latest/glossary/#term-Wheel)
  file distributed by the
  [package index](https://packaging.python.org/en/latest/glossary/#term-Package-Index)
  and therefore increase build, download and installation times.
  Another approach is to use a Python entry-point that calls the Rust
  implementation (exposed via PyO3 bindings).
  See the [hello-world](https://github.com/PyO3/setuptools-rust/tree/main/examples/hello-world)
  example for more insights.

- For a complete reference of the configuration options, see the
  [API reference](https://setuptools-rust.readthedocs.io/en/latest/reference.html).
  You can use any parameter defined by the `RustExtension` class with
  `[[tool.setuptools-rust.ext-modules]]` and any parameter defined by the
  `RustBin` class with `[[tool.setuptools-rust.bins]]`; just remember to replace
  underscore characters `_` with dashes `-` in your `pyproject.toml` file.

- `Cargo.toml` allow only one `[lib]` table per file.
  If you require multiple extension modules you will need to write multiple `Cargo.toml` files.
  Alternatively you can create a single private Rust top-level module that exposes
  multiple submodules (using [PyO3's submodules](https://pyo3.rs/v0.20.0/module#python-submodules)),
  which may also reduce the size of the build artifacts.
  You can always keep your extension modules private and wrap them in pure Python
  to have fine control over the public API.

- If want to include both `[[tool.setuptools-rust.bins]]` and `[[tool.setuptools-rust.ext-modules]]`
  in the same macOS wheel, you might have to manually add an extra `build.rs` file,
  see [PyO3/setuptools-rust#351](https://github.com/PyO3/setuptools-rust/pull/351)
  for more information about the workaround.

- For more examples, see:
  - [`hello-world`](https://github.com/PyO3/setuptools-rust/tree/main/examples/hello-world):
    a more complete version of the code used in this tutorial that mixes both
    `[[tool.setuptools-rust.ext-modules]]` and `[[tool.setuptools-rust.bins]]`
    in a single distribution.
  - [`html-py-ever`](https://github.com/PyO3/setuptools-rust/tree/main/examples/html-py-ever):
    a more advanced example that uses Rust crates as dependencies.
  - [`rust_with_cffi`](https://github.com/PyO3/setuptools-rust/tree/main/examples/rust_with_cffi):
    uses both Rust and [CFFI](https://cffi.readthedocs.io/en/latest/).
  - [`namespace_package`](https://github.com/PyO3/setuptools-rust/tree/main/examples/namespace_package):
    integrates Rust-written modules into PEP 420 namespace packages.
  - [`hello-world-script`](https://github.com/PyO3/setuptools-rust/tree/main/examples/hello-world-script):
    uses Rust only for creating binary executables, not library modules.
