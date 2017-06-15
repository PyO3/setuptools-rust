from __future__ import print_function, absolute_import
import glob
import os
import shutil
import sys
import subprocess
from distutils.cmd import Command
from distutils.errors import (
    CompileError, DistutilsExecError, DistutilsFileError,
    DistutilsPlatformError)

from .extension import RustExtension
from .utils import cpython_feature, get_rust_version


class build_rust(Command):
    """ Command for building rust crates via cargo. """

    description = "build Rust extensions (compile/link to build directory)"

    user_options = [
        ('inplace', 'i',
         "ignore build-lib and put compiled extensions into the source " +
         "directory alongside your pure Python modules"),
        ('debug', 'd',
         "Force debug to true for all rust extensions "),
        ('release', 'r',
         "Force debug to false for all rust extensions "),
        ('qbuild', None,
         "Force enable quiet option for all rust extensions "),
    ]
    boolean_options = ['inplace', 'debug', 'release', 'qbuild']

    def initialize_options(self):
        self.extensions = ()
        self.inplace = None
        self.debug = None
        self.release = None
        self.qbuild = None

    def finalize_options(self):
        self.extensions = [ext for ext in self.distribution.rust_extensions
                           if isinstance(ext, RustExtension)]

    def build_extension(self, ext):
        # Make sure that if pythonXX-sys is used, it builds against the current
        # executing python interpreter.
        bindir = os.path.dirname(sys.executable)

        env = os.environ.copy()
        env.update({
            # disables rust's pkg-config seeking for specified packages,
            # which causes pythonXX-sys to fall back to detecting the
            # interpreter from the path.
            "PATH":  bindir + os.pathsep + os.environ.get("PATH", "")
        })

        if not os.path.exists(ext.path):
            raise DistutilsFileError(
                "Can not file rust extension project file: %s" % ext.path)

        features = set(ext.features)
        features.update(cpython_feature(binding=ext.binding))

        if ext.debug is None:
            debug_build = self.inplace
        else:
            debug_build = ext.debug

        debug_build = self.debug if self.debug is not None else debug_build
        if self.release:
            debug_build = False

        quiet = self.qbuild or ext.quiet

        # build cargo command
        feature_args = ["--features", " ".join(features)] if features else []
        args = (["cargo", "rustc", "--lib", "--manifest-path", ext.path]
                + feature_args
                + list(ext.args or []))
        if not debug_build:
            args.append("--release")
        if quiet:
            args.append("-q")

        args.extend(["--", '--crate-type', 'cdylib'])

        # OSX requires special linker argument
        if sys.platform == "darwin":
            args.extend(["-C", "link-arg=-undefined",
                         "-C", "link-arg=dynamic_lookup"])

        if not quiet:
            print(" ".join(args), file=sys.stderr)

        # Execute cargo
        try:
            output = subprocess.check_output(args, env=env)
        except subprocess.CalledProcessError as e:
            output = e.output
            if isinstance(output, bytes):
                output = e.output.decode('latin-1').strip()
            raise CompileError(
                "cargo failed with code: %d\n%s" % (e.returncode, output))

        except OSError:
            raise DistutilsExecError(
                "Unable to execute 'cargo' - this package "
                "requires rust to be installed and cargo to be on the PATH")

        if not quiet:
            if isinstance(output, bytes):
                output = output.decode('latin-1')
            if output:
                print(output, file=sys.stderr)

        # Find the shared library that cargo hopefully produced and copy
        # it into the build directory as if it were produced by build_ext.
        if debug_build:
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
                "rust build failed; unable to find any %s in %s" %
                (wildcard_so, target_dir))

        # Ask build_ext where the shared library would go if it had built it,
        # then copy it there.
        build_ext = self.get_finalized_command('build_ext')
        build_ext.inplace = self.inplace
        target_fname = ext.name
        if target_fname is None:
            target_fname = os.path.basename(os.path.splitext(
                os.path.basename(dylib_path)[3:])[0])

        ext_path = build_ext.get_ext_fullpath(target_fname)
        try:
            os.makedirs(os.path.dirname(ext_path))
        except OSError:
            pass
        shutil.copyfile(dylib_path, ext_path)

    def run(self):
        if not self.extensions:
            return

        version = get_rust_version()

        for ext in self.extensions:
            rust_version = ext.get_rust_version()
            if rust_version is not None and version not in rust_version:
                raise DistutilsPlatformError(
                    "Rust %s does not match extension requirement %s" % (
                        version, ext.rust_version))

            self.build_extension(ext)
