from __future__ import print_function, absolute_import
import os
import sys
from distutils.errors import DistutilsSetupError

import semantic_version


class RustExtension:
    """Just a collection of attributes that describes an rust extension
    module and everything needed to build it

    Instance attributes:
      name : string
        the full name of the extension, including any packages -- ie.
        *not* a filename or pathname, but Python dotted name
      path : string
        path to the cargo.toml manifest file
      args : [string]
        a list of extra argumenents to be passed to cargo.
      features : [string]
        a list of features to also build
      rust_version : string
        rust compiler version
      quiet : bool
        If True, doesn't echo cargo's output.
      debug : bool
        Controls whether --debug or --release is passed to cargo. If set to
        None then build type is auto-detect. Inplace build is debug build
        otherwise release. Default: None
      pyo3 : bool
        Controls which python binding is in use. `pyo3=True` uses PyO3 binding,
        `pyo3=False` uses rust-cpython binding,
      no_binding : bool
        If you don't want to run `pyo3` or `rust-cpython`, set this to True.
        Useful if you want to use a different interface like CFFI.

    """

    def __init__(self, name, path,
                 args=None, features=None, rust_version=None,
                 quiet=False, debug=None, pyo3=False, no_binding=False):
        self.name = name
        self.args = args
        self.pyo3 = pyo3
        self.rust_version = rust_version
        self.quiet = quiet
        self.debug = debug
        self.no_binding = no_binding

        if features is None:
            features = []

        self.features = [s.strip() for s in features]

        # get absolute path to Cargo manifest file
        file = sys._getframe(1).f_globals.get('__file__')
        if file:
            dirname = os.path.dirname(file)
            if dirname:
                cwd = os.getcwd()
                os.chdir(dirname)
                path = os.path.abspath(path)
                os.chdir(cwd)

        self.path = path

    def get_rust_version(self):
        if self.rust_version is None:
            return None
        try:
            return semantic_version.Spec(self.rust_version)
        except:
            raise DistutilsSetupError(
                'Can not parse rust compiler version: %s', self.rust_version)
