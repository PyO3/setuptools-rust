# Building wheels

Because `setuptools-rust` is an extension to `setuptools`, the standard [`python -m build`](https://pypa-build.readthedocs.io/en/stable/) command
(or [`pip wheel --no-deps . --wheel-dir dist`](https://pip.pypa.io/en/stable/cli/pip_wheel/)) can be used to build distributable wheels.
These wheels can be uploaded to PyPI using standard tools such as [twine](https://github.com/pypa/twine).

A key choice to make is whether to upload [PEP 384](https://www.python.org/dev/peps/pep-0384/) "stable" (aka "limited") API wheels which support multiple Python versions in a single binary, or to build individual artifacts for each Python version. There is a longer discussion of this [in the PyO3 docs](https://pyo3.rs/latest/building_and_distribution#py_limited_apiabi3).

This chapter covers each of these options below.

## Building for ABI3

`setuptools-rust` will automatically configure for the limited API when this is set in the `[bdist_wheel]` configuration section of [`setup.cfg`](https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html#writing-the-setup-configuration-file):

```ini
[bdist_wheel]
py_limited_api=cp37  # replace with desired minimum Python version
```

If using a `pyproject.toml`-based build, then save the above in a file and use the `DIST_EXTRA_CONFIG` environment variable to instruct `setuptools` to pick up this extra configuration. (`DIST_EXTRA_CONFIG` is documented [on this page](https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html#writing-the-setup-configuration-file) of the `setuptools` docs.)

It is also possible to pass this setting via the command line, e.g.

```
python -m build --config-settings=--build-option=--py-limited-api=cp37
```

## Building for multiple Python versions

### Using `cibuildwheel`

[`cibuildwheel`][cibuildwheel] is a tool to build wheels for multiple platforms using Github Actions.

The [`rtoml` package does this, for example](https://github.com/samuelcolvin/rtoml/blob/143ee0907bba616cbcd5cc58eefe9000fcc2b5f2/.github/workflows/ci.yml#L99-L195).

### Building manually

Place a script called `build-wheels.sh` with the following contents in your project root (next to the `setup.py` file):

```{eval-rst}
.. literalinclude:: ../examples/html-py-ever/build-wheels.sh
   :language: bash
```

This script can be used to produce wheels for multiple Python versions.

#### Binary wheels on linux

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

#### Binary wheels on macOS

For building wheels on macOS it is sufficient to use one of the default `python -m build` or `pip wheel --no-deps . --wheel-dir dist` commands.

To build `universal2` wheels set the `ARCHFLAGS` environment variable to contain both `x86_64` and `arm64`, for example `ARCHFLAGS="-arch x86_64 -arch arm64"`. Wheel-building solutions such as [`cibuildwheel`][cibuildwheel] set this environment variable automatically.

[cibuildwheel]: https://github.com/pypa/cibuildwheel
