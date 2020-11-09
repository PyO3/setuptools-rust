`example_tomlgen`
=================

An example extension with automatically generated ``Cargo.toml`` manifest
files. Simply run ``python setup.py tomlgen_rust`` to generate the following
files:

* ``Cargo.toml`` for ``hello-english``

.. code-block:: toml

    [package]
    name = "hello-english"
    version = "0.1.0"
    authors = ["Martin Larralde <martin.larralde@ens-paris-saclay.fr>"]
    publish = false

    [lib]
    crate-type = ["cdylib"]
    name = "hello_english"
    path = "lib.rs"

    [dependencies]
    pyo3 = { version = "*", features = ["extension-module"] }
    english-lint = "*"


* ``Cargo.toml`` for ``hello.french``

.. code-block:: toml

    [package]
    name = "hello.french"
    version = "0.1.0"
    authors = ["Martin Larralde <martin.larralde@ens-paris-saclay.fr>"]
    publish = false

    [lib]
    crate-type = ["cdylib"]
    name = "hello_french"
    path = "lib.rs"

    [dependencies]
    pyo3 = { version = "*", features = ["extension-module"] }


Metadata
--------

The package name will be generated from the position of the extension within
the Python package. The same version is used as the one declared in ``setup.py``
or ``setup.cfg``.

The authors list is generated after the ``author`` and ``author_email`` options
from ``setup.py`` / ``setup.cfg``, but can also be overriden using the
``authors`` key in the ``[tomlgen_rust]`` section of ``setup.cfg``:

.. code-block:: ini

    [tomlgen_rust]
    authors =
      Jane Doe <jane@doe.name>
      John Doe <john@doe.name>

The library name is a slugified variant of the extension package name, to
avoid name collisions within the build directory.

As a safety, ``publish = false`` is added to the ``[package]`` section
(you wouldn't publish an automatically generated package, *would you ?!*).


Options
-------

Use ``--force`` (or add ``force = true`` to the ``[tomlgen_rust]`` section of
``setup.cfg``) to force generating a manifest even when one already exists.

Use ``--create-workspace`` to create a virtual manifest at the root of your
project (next to the ``setup.py`` file) which registers all of the extensions.
This way, generic ``cargo`` commands can be run without leaving the root of
the project.

If ``--create-workspace`` is enabled, a `.cargo/config` file will also be
created to force ``cargo`` to build to the temporary build directory. Use
``--no-config`` to disable.


Dependencies
------------

To specify dependencies for all extensions, add them to the
``[tomlgen_rust.dependencies]`` section of your setuptools configuration file
(``setup.cfg``), as you would normally in your ``Cargo.toml`` file. Here is
probably a good place to add ``pyo3`` as a dependency.

To specify per-extension dependency, create a section for each extension
(``[tomlgen_rust.dependencies.<DOTTEDPATH>]``, where ``<DOTTEDPATH>`` is the
complete Python path to the extension (e.g. ``hello-english``). Extension
specific dependencies are added *after* global dependencies.

*Note that, since all projects are built in the same directory, you can also
declare all dependencies in the* ``[tomlgen_rust.dependencies]``, *as they will
be built only once anyway*.


Automatic generation at each build
----------------------------------

If you intend to regenerate manifests everytime the library is built, you can
add ``Cargo.toml`` and ``Cargo.lock`` to your ``.gitignore`` file.

Then, make sure ``tomlgen_rust`` is run before ``build_rust`` everytime by
adding aliases to your ``setup.cfg`` file:

.. code-block:: ini

    [aliases]
    build_rust = tomlgen_rust -f build_rust
    clean_rust = tomlgen_rust -f clean_rust
    build = tomlgen_rust -f build
    clean = clean_rust -f clean
