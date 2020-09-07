from __future__ import print_function, absolute_import
import os
import re
from distutils.errors import DistutilsSetupError
from .utils import Binding, Strip

import semantic_version


class RustExtension:
    """Just a collection of attributes that describes an rust extension
    module and everything needed to build it

    Instance attributes:
      target : string
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
      strip : setuptools_rust.Strip
        Strip symbols from final file. Does nothing for debug build.
        * Strip.No - do not strip symbols
        * Strip.Debug - strip debug symbols
        * Strip.All - strip all symbols
      script : bool
        Generate console script for executable if `Binding.Exec` is used.
      native : bool
        Build extension or executable with "target-cpu=native"
      optional : bool
        if it is true, a build failure in the extension will not abort the
        build process, but instead simply not install the failing extension.
      py_limited_api : bool
        Same as `py_limited_api` on `setuptools.Extension`. Note that if you
        set this to True, your extension must pass the appropriate feature
        flags to pyo3 (ensuring that `abi3` feature is enabled).
    """

    def __init__(
        self,
        target,
        path="Cargo.toml",
        args=None,
        features=None,
        rustc_flags=None,
        rust_version=None,
        quiet=False,
        debug=None,
        binding=Binding.PyO3,
        strip=Strip.No,
        script=False,
        native=False,
        optional=False,
        py_limited_api=False,
    ):
        if isinstance(target, dict):
            name = "; ".join("%s=%s" % (key, val) for key, val in target.items())
        else:
            name = target
            target = {"": target}

        self.name = name
        self.target = target
        self.args = args
        self.rustc_flags = rustc_flags
        self.binding = binding
        self.rust_version = rust_version
        self.quiet = quiet
        self.debug = debug
        self.strip = strip
        self.script = script
        self.native = native
        self.optional = optional
        self.py_limited_api = py_limited_api
        # We pass this over to setuptools in one place, and it wants this
        # attribute to exist.
        self._links_to_dynamic = False

        if features is None:
            features = []

        self.features = [s.strip() for s in features]

        # get relative path to Cargo manifest file
        path = os.path.relpath(path)
        # file = sys._getframe(1).f_globals.get('__file__')
        # if file:
        #     dirname = os.path.dirname(file)
        #     print(dirname)
        #     if dirname:
        #         cwd = os.getcwd()
        #         os.chdir(dirname)
        #         path = os.path.abspath(path)
        #         os.chdir(cwd)

        self.path = path

    def get_lib_name(self):
        """ Parse Cargo.toml to get the name of the shared library. """
        # We import in here to make sure the the setup_requires are already installed
        import toml

        cfg = toml.load(self.path)
        name = cfg.get("lib", {}).get("name")
        if name is None:
            name = cfg.get("package", {}).get("name")
        if name is None:
            raise Exception(
                "Can not parse library name from Cargo.toml. "
                "Cargo.toml missing value for 'name' key "
                "in both the [package] section and the [lib] section"
            )
        name = re.sub(r"[./\\-]", "_", name)
        return name

    def get_rust_version(self):
        if self.rust_version is None:
            return None
        try:
            return semantic_version.Spec(self.rust_version)
        except ValueError:
            raise DistutilsSetupError(
                "Can not parse rust compiler version: %s", self.rust_version
            )

    def entry_points(self):
        entry_points = []
        if self.script and self.binding == Binding.Exec:
            for name, mod in self.target.items():
                base_mod, name = mod.rsplit(".")
                script = "%s=%s.%s:run" % (name, base_mod, "_gen_%s" % name)
                entry_points.append(script)

        return entry_points

    def install_script(self, ext_path):
        if self.script and self.binding == Binding.Exec:
            dirname, name = os.path.split(ext_path)
            file = os.path.join(dirname, "_gen_%s.py" % name)
            with open(file, "w") as f:
                f.write(TMPL.format({"name": name}))


TMPL = """from __future__ import absolute_import, print_function

import os
import sys


def run():
    path = os.path.split(__file__)[0]
    name = os.path.split(sys.argv[0])[1]
    file = os.path.join(path, name)
    if os.path.isfile(file):
        os.execv(file, sys.argv)
    else:
        print("Can not execute '%s'" % name)
"""
