# Building wheels

Because `setuptools-rust` is an extension to `setuptools`, the standard `setup.py bdist_wheel` command is used to build distributable wheels. These wheels can be uploaded to PyPI using standard tools such as [twine](https://github.com/pypa/twine).

`setuptools-rust` supports building for the [PEP 384](https://www.python.org/dev/peps/pep-0384/) "stable" (aka "limited") API when the `--py-limited-api` option is passed to `setup.py bdist_wheel`. If using PyO3 bindings for `RustExtension`, then the correct [`pyo3/abi3`](https://pyo3.rs/v0.14.5/features.html#abi3) sub-feature is automatically enabled. In this way, abi3 wheels can be uploaded to make package distributors' roles easier, and  package users installing from source with `python setup.py install` can use optimizations specific to their Python version.

This chapter of the documentation explains two possible ways to build wheels for multiple Python versions below.

## Using `cibuildwheel`

[`cibuildwheel`][cibuildwheel] is a tool to build wheels for multiple platforms using Github Actions.

The [`rtoml` package does this, for example](https://github.com/samuelcolvin/rtoml/blob/143ee0907bba616cbcd5cc58eefe9000fcc2b5f2/.github/workflows/ci.yml#L99-L195).

## Building manually

Place a script called `build-wheels.sh` with the following contents in your project root (next to the `setup.py` file):

```{eval-rst}
.. literalinclude:: ../examples/html-py-ever/build-wheels.sh
   :language: bash
```

This script can be used to produce wheels for multiple Python versions.

### Binary wheels on linux

To build binary wheels on linux, you need to use the [manylinux docker container](https://github.com/pypa/manylinux). You will run the `build-wheels.sh` from above inside that container.

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
hello_rust-0.1.0-cp37-cp37m-linux_x86_64.whl          hello_rust-0.1.0-cp37-cp37m-manylinux2014_x86_64.whl
hello_rust-0.1.0-cp38-cp38-linux_x86_64.whl           hello_rust-0.1.0-cp38-cp38-manylinux2014_x86_64.whl
hello_rust-0.1.0-cp39-cp39-linux_x86_64.whl           hello_rust-0.1.0-cp39-cp39-manylinux2014_x86_64.whl
```

It is possible to use any of the `manylinux` docker images: `manylinux1`, `manylinux2010` or `manylinux2014`. (Just replace `manylinux2014` in the above instructions with the alternative version you wish to use.)

### Binary wheels on macOS

For building wheels on macOS it is sufficient to run the `bdist_wheel` command, i.e. `setup.py bdist_wheel`.

To build `universal2` wheels set the `ARCHFLAGS` environment variable to contain both `x86_64` and `arm64`, for example `ARCHFLAGS="-arch x86_64 -arch arm64"`. Wheel-building solutions such as [`cibuildwheel`][cibuildwheel] set this environment variable automatically.

[cibuildwheel]: https://github.com/pypa/cibuildwheel
