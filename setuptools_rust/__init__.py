from __future__ import print_function
import glob
import os
import shutil
import sys
import subprocess
from distutils.cmd import Command
from distutils.dist import Distribution
from distutils.command.build import build as Build
from distutils.command.build_ext import build_ext
from distutils.command.install_lib import install_lib
from setuptools import setup, Extension
from setuptools.command import develop

__all__ = ('RustExtension', 'build_rust')


# allow to use 'rust_extensions' parameter for setup() call
Distribution.rust_extensions = ()


# add support for build_rust sub0command
def has_rust_extensions(self):
    exts = [ext for ext in self.distribution.rust_extensions
            if isinstance(ext, RustExtension)]
    return bool(exts)


Build.has_rust_extensions = has_rust_extensions
Build.sub_commands.append(('build_rust', Build.has_rust_extensions))

# monkey patch "develop" command
orig_run_command = develop.develop.run_command

def monkey_run_command(self, cmd):
    orig_run_command(self, cmd)

    if cmd == 'build_ext':
        self.reinitialize_command('build_rust', inplace=1)
        orig_run_command(self, 'build_rust')

develop.develop.run_command = monkey_run_command


class RustExtension:
    """Just a collection of attributes that describes an rust extension
    module and everything needed to build it

    Instance attributes:
      name : string
        the full name of the extension, including any packages -- ie.
        *not* a filename or pathname, but Python dotted name
      path : string
        path to the cargo.toml manifest
      args : [stirng]
        a list of extra argumenents to be passed to cargo.
      quiet : bool
        If True, doesn't echo cargo's output.
      debug : bool
        Controls whether --debug or --release is passed to cargo.
    """

    def __init__(self, name, path, args=None, quiet=False, debug=False):
        self.name=name
        self.path=path
        self.args=args
        self.quiet=quiet
        self.debug=debug


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

    def features(self):
        version = sys.version_info
        if (2,7) < version < (2,8):
            return "python27-sys"
        elif (3,3) < version:
            return "python3-sys"
        else:
            raise ValueError("Unsupported python version: %s" % sys.version)

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

        # Execute cargo.
        try:
            args = (["cargo", "build", "--manifest-path", ext.path,
                     "--features", self.features()] + list(ext.args or []))
            if not ext.debug:
                args.append("--release")
            if not ext.quiet:
                print(" ".join(args), file=sys.stderr)
                output = subprocess.check_output(args, env=env)
        except subprocess.CalledProcessError as e:
            msg = "cargo failed with code: %d\n%s" % (e.returncode, e.output)
            raise Exception(msg)
        except OSError:
            raise Exception("Unable to execute 'cargo' - this package "
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
            raise Exception(
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
        for ext in self.extensions:
            self.build_extension(ext)
