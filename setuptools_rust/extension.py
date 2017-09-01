from __future__ import print_function, absolute_import
import os
import os.path
import sys
from distutils.errors import DistutilsSetupError
from .utils import Binding, Strip


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
      binding : setuptools_rust.Binding
        Controls which python binding is in use.
        Binding.PyO3 uses PyO3
        Binding.RustCPython uses Rust CPython.
        Binding.NoBinding uses no binding.
        Binding.Exec build executable.
      strip : setuptools_rust.Binding
        Strip symbols from final file. Does nothing for debug build.
        * Strip.No - do not strip symbols
        * Strip.Debug - strip debug symbols
        * Strip.All - strip all symbols
      script : bool
        Generate console script for executable if `Binding.Exec` is used.
      optional : bool
        if it is true, a build failure in the extension will not abort the
        build process, but instead simply not install the failing extension.
    """

    def __init__(self, name, path,
                 args=None, features=None, rust_version=None,
                 quiet=False, debug=None, binding=Binding.PyO3,
                 strip=Strip.No, script=False, optional=False):
        self.name = name
        self.args = args
        self.binding = binding
        self.rust_version = rust_version
        self.quiet = quiet
        self.debug = debug
        self.strip = strip
        self.script = script
        self.optional = optional

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

    def entry_points(self):
        entry_points = []
        if self.script and self.binding == Binding.Exec:
            base_mod, name = self.name.rsplit('.')
            script = '%s=%s.%s:run' % (name, base_mod, '_gen_%s' % name)
            entry_points.append(script)

        return entry_points

    def install_script(self, ext_path):
        if self.script and self.binding == Binding.Exec:
            dirname, name = os.path.split(ext_path)
            file = os.path.join(dirname, '_gen_%s.py' % name)
            with open(file, 'w') as f:
                f.write(TMPL.format({'name': name}))


TMPL = """from __future__ import absolute_import, print_function

import os
import sys


def run():
    path = os.path.split(__file__)[0]
    file = os.path.join(path, "%(name)")
    if os.path.isfile(file):
        os.execv(file, sys.argv)
    else:
        print("Can not execute %(name)")

"""
