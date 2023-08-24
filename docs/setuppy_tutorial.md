# Usage with `setup.py`

While `pyproject.toml`-based configuration will be enough for most projects,
sometimes you may need to use custom logic and imperative programming during the build.
For those scenarios, `setuptools` also allows you to specify project configuration
via `setup.py` in addition to `pyproject.toml`.

The following is a very basic tutorial that shows how to use `setuptools-rust` in
your `setup.py`.


## Basic implementation files

Let's start by assuming that you already have a bunch of Python and Rust files[^1]
that you would like to package for distribution in PyPI inside of a project directory
named `hello-world-setuppy`[^2][^3]:

[^1]: To know more about how to write Rust to be integrated into Python packages,
      please have a look on the [PyO3 docs](https://pyo3.rs)
[^2]: You can have a look on the
      [examples/hello-world-setuppy](https://github.com/PyO3/setuptools-rust/tree/main/examples/hello-world-setuppy)
      directory in the `setuptools-rust` repository.
[^3]: If you are an experienced Python or Rust programmer, you may notice that we
      avoid using the `src` directory and explicitly instruct Setuptools and Cargo to
      look into the `python` and `rust` directories respectively.
      Since both Python and Rust ecosystem will try to claim the `src` directory as
      their default, we prefer to be explicit and avoid confusion.


```
hello-world-setuppy
├── Cargo.lock
├── Cargo.toml
├── python
│   └── hello_world
│       └── __init__.py
└── rust
    └── lib.rs
```

```{literalinclude} ../examples/hello-world-setuppy/python/hello_world/__init__.py
   :language: python
```

```{literalinclude} ../examples/hello-world-setuppy/rust/lib.rs
   :language: rust
```

```{literalinclude} ../examples/hello-world-setuppy/Cargo.toml
   :language: toml
```


## Adding files to support packaging

Now we start by adding a `pyproject.toml` which tells anyone that wants to use
our project to use `setuptools` and `setuptools-rust` to build it:

```{literalinclude} ../examples/hello-world-setuppy/pyproject.toml
   :language: toml
```

… and a [`setup.py` configuration file](https://setuptools.pypa.io/en/latest/references/keywords.html)
that tells Setuptools how to build the Rust extensions using our `Cargo.toml` and `setuptools-rust`:

```{literalinclude} ../examples/hello-world-setuppy/setup.py
   :language: python
```

For a complete reference of the options supported by the `RustExtension` class, see the
[API reference](https://setuptools-rust.readthedocs.io/en/latest/reference.html).


We also add a [`MANIFEST.in` file](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html)
to control which files we want in the source distribution[^4]:

```{literalinclude} ../examples/hello-world-setuppy/MANIFEST.in
```

[^4]: Alternatively you can also use `setuptools-scm` to add all the files under revision control
      to the `sdist`, see the [docs](https://pypi.org/project/setuptools-scm/) for more information.


## Testing the extension

With these files in place, you can install the project in a virtual environment
for testing and making sure everything is working correctly:


```powershell
# cd hello-world-setuppy
python3 -m venv .venv
source .venv/bin/activate  # on Linux or macOS
.venv\Scripts\activate     # on Windows
python -m pip install -e .
python -c 'import hello_world; print(hello_world.sum_as_string(5, 7))'  # => 12
# ... better write some tests with pytest ...
```


## Next steps and final remarks

- When you are ready to distribute your project, have a look on
  [the notes in the documentation about building wheels](https://setuptools-rust.readthedocs.io/en/latest/building_wheels.html).

- You can also use a [`RustBin`](https://setuptools-rust.readthedocs.io/en/latest/reference.html) object
  (instead of a `RustExtension`), if you want to distribute a binary executable
  written in Rust (instead of a library that can be imported by the Python runtime).
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

- If want to include both `RustBin` and `RustExtension` same macOS wheel, you might have
  to manually add an extra `build.rs` file, see [PyO3/setuptools-rust#351](https://github.com/PyO3/setuptools-rust/pull/351)
  for more information about the workaround.

- Since the adoption of {pep}`517`, running `python setup.py ...` directly as a CLI tool is
  [considered deprecated](https://blog.ganssle.io/articles/2021/10/setup-py-deprecated.html).
  Nevertheless, `setup.py` can be safely used as a configuration file
  (the same way `conftest.py` is used by `pytest` or `noxfile.py` is used by `nox`).
  There is a different mindset that comes with this change, though:
  for example, it does not make sense to use `sys.exit(0)` in a `setup.py` file
  or use a overarching `try...except...` block to re-run a failed build with different parameters.
