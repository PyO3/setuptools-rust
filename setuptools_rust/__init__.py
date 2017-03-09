from __future__ import print_function, absolute_import
import glob
import os
import shutil
import sys
import subprocess
from distutils.cmd import Command
from distutils.errors import (
    CompileError,
    DistutilsExecError, DistutilsFileError, DistutilsPlatformError)

import semver

from . import patch  # noqa

__all__ = ('RustExtension', 'build_rust')


class RustExtension:
    """Just a collection of attributes that describes an rust extension
    module and everything needed to build it

    Instance attributes:
      name : string
        the full name of the extension, including any packages -- ie.
        *not* a filename or pathname, but Python dotted name
      path : string
        path to the cargo.toml manifest
      args : [string]
        a list of extra argumenents to be passed to cargo.
      features : [string]
        a list of features to also build
      rust_version : string
        rust compiler version
      quiet : bool
        If True, doesn't echo cargo's output.
      debug : bool
        Controls whether --debug or --release is passed to cargo.
    """

    def __init__(self, name, path,
                 args=None, features=None, rust_version=None,
                 quiet=False, debug=False):
        self.name = name
        self.path = path
        self.args = args
        self.rust_version = rust_version
        self.quiet = quiet
        self.debug = debug

        if features is None:
            features = []

        self.features = [s.strip() for s in features]

    @staticmethod
    def get_rust_version():
        env = os.environ.copy()
        try:
            output = subprocess.check_output(["rustc", "-V"], env=env)
            return output.split(' ')[1]
        except subprocess.CalledProcessError:
            return None
        except OSError:
            return None


class build_rust(Command):
    """
    Command for building rust crates via cargo.

    Don't use this directly; use the build_rust_cmdclass
    factory method.
    """
    description = "build rust crates into Python extensions"

    user_options = [
        ('inplace', 'i',
         "ignore build-lib and put compiled extensions into the source " +
         "directory alongside your pure Python modules"),
    ]

    def initialize_options(self):
        self.extensions = ()
        self.inplace = False

    def finalize_options(self):
        self.extensions = [ext for ext in self.distribution.rust_extensions
                           if isinstance(ext, RustExtension)]

    def _cpython_feature(self):
        version = sys.version_info
        if (2, 7) < version < (2, 8):
            return "cpython/python27-sys"
        elif (3, 3) < version:
            return "cpython/python3-sys"
        else:
            raise DistutilsPlatformError(
                "Unsupported python version: %s" % sys.version)

    def build_extension(self, ext):
        # Make sure that if pythonXX-sys is used, it builds against the current
        # executing python interpreter.
        bindir = os.path.dirname(sys.executable)

        env = os.environ.copy()
        env.update({
            # disables rust's pkg-config seeking for specified packages,
            # which causes pythonXX-sys to fall back to detecting the
            # interpreter from the path.
            "PYTHON_2.7_NO_PKG_CONFIG": "1",
            "PATH":  bindir + os.pathsep + os.environ.get("PATH", "")
        })

        if not os.path.exists(ext.path):
            raise DistutilsFileError(
                "Can not file rust extension project file: %s" % ext.path)

        features = set(ext.features)
        features.add(self._cpython_feature())

        # Execute cargo.
        try:
            args = (["cargo", "build", "--manifest-path", ext.path,
                     "--features", " ".join(features)] + list(ext.args or []))
            if not ext.debug:
                args.append("--release")
            if not ext.quiet:
                print(" ".join(args), file=sys.stderr)
                output = subprocess.check_output(args, env=env)
        except subprocess.CalledProcessError as e:
            raise CompileError(
                "cargo failed with code: %d\n%s" % (e.returncode, e.output))
        except OSError:
            raise DistutilsExecError(
                "Unable to execute 'cargo' - this package "
                "requires rust to be installed and cargo to be on the PATH")

        if not ext.quiet:
            print(output, file=sys.stderr)

        # Find the shared library that cargo hopefully produced and copy
        # it into the build directory as if it were produced by build_cext.
        if ext.debug:
            suffix = "debug"
        else:
            suffix = "release"

        target_dir = os.path.join(os.path.dirname(ext.path), "target/", suffix)

        if sys.platform == "win32":
            wildcard_so = "*.dll"
        elif sys.platform == "darwin":
            wildcard_so = "*.dylib"
        else:
            wildcard_so = "*.so"

        try:
            dylib_path = glob.glob(os.path.join(target_dir, wildcard_so))[0]
        except IndexError:
            raise DistutilsExecError(
                "rust build failed; unable to find any .dylib in %s" %
                target_dir)

        # Ask build_ext where the shared library would go if it had built it,
        # then copy it there.
        build_ext = self.get_finalized_command('build_ext')
        build_ext.inplace = self.inplace
        target_fname = ext.name
        if target_fname is None:
            target_fname = os.path.splitext(
                os.path.basename(dylib_path)[3:])[0]

        ext_path = build_ext.get_ext_fullpath(os.path.basename(target_fname))
        try:
            os.makedirs(os.path.dirname(ext_path))
        except OSError:
            pass
        shutil.copyfile(dylib_path, ext_path)

    def run(self):
        version = RustExtension.get_rust_version()
        if self.extensions and version is None:
            raise DistutilsPlatformError('Can not find Rust compiler')

        for ext in self.extensions:
            if ext.rust_version is not None:
                if not semver.match(version, ext.rust_version):
                    raise DistutilsPlatformError(
                        "Rust %s does not match extension requirenment %s" % (
                            version, ext.rust_version))

            self.build_extension(ext)
