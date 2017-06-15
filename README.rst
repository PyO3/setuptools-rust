Setuptools helpers for rust Python extensions.

Compile and distribute Python extensions written in rust as easily as if they were written in C.

Example
-------

setup.py
^^^^^^^^

.. code-block:: python

   from setuptools import setup
   from setuptools_rust import Binding, RustExtension

   setup(name='hello-rust',
         version='1.0',
         rust_extensions=[RustExtension('hello_rust._helloworld',
                                        'Cargo.toml', binding=Binding.PyO3)],
         packages=['hello_rust'],
         # rust extensions are not zip safe, just like C-extensions.
         zip_safe=False
   )


You can use same commands as for c-extensions. For example::

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


Or you can use commands like `bdist_wheel` or `bdist_egg`


RustExtension
-------------

You can define rust extension with `RustExtension` class:

   RustExtension(name, path, args=None, features=None, rust_version=None, quiet=False, debug=False)

   The class for creating rust extensions.

   :param str name: the full name of the extension, including any packages -- ie.
                    *not* a filename or pathname, but Python dotted name

   :param str path: path to the Cargo.toml manifest file

   :param [str] args: a list of extra argumenents to be passed to cargo.

   :param [str] features: a list of features to also build

   :param str rust_version: sematic version of rust compiler version -- for example
                            *>1.14,<1.16*, default is None

   :param bool quiet: Does not echo cargo's output. default is False

   :param bool debug: Controls whether --debug or --release is passed to cargo. If set to
                      None then build type is auto-detect. Inplace build is debug build
                      otherwise release. Default: None

   :param int binding: Controls which python binding is in use.
                       `Binding.PyO3` uses PyO3
                       `Binding.RustCPython` uses rust-cpython
                       `Binding.NoBinding` uses no binding.

Commands
--------

* `build` - Standard `build` command builds all rust extensions.

* `build_ext` - Command builds all rust extensions.

* `clean` - Standard `clean` command executes `cargo clean` for all rust extensions.

* `check` - Standard `check` command executes `cargo check` for all rust extensions.
