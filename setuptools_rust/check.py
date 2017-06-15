from __future__ import print_function, absolute_import
import os
import sys
import subprocess
from distutils.cmd import Command
from distutils.errors import (
    CompileError, DistutilsFileError, DistutilsExecError)

import semantic_version

from .extension import RustExtension
from .utils import cpython_feature, get_rust_version

MIN_VERSION = semantic_version.Spec('>=1.16')


class check_rust(Command):
    """ Run rust check"""

    description = "check rust extensions"

    def initialize_options(self):
        self.extensions = ()

    def finalize_options(self):
        self.extensions = [ext for ext in self.distribution.rust_extensions
                           if isinstance(ext, RustExtension)]

    def run(self):
        if not self.extensions:
            return

        version = get_rust_version()
        if version not in MIN_VERSION:
            print('Rust version mismatch: required rust%s got rust%s' % (
                MIN_VERSION,  version))
            return

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

        for ext in self.extensions:
            if not os.path.exists(ext.path):
                raise DistutilsFileError(
                    "Can not file rust extension project file: %s" % ext.path)

            features = set(ext.features)
            features.update(cpython_feature(binding=ext.binding))

            # check cargo command
            feature_args = ["--features", " ".join(features)] if features else []
            args = (["cargo", "check", "--lib", "--manifest-path", ext.path]
                    + feature_args
                    + list(ext.args or []))

            # Execute cargo command
            try:
                subprocess.check_output(args)
            except subprocess.CalledProcessError as e:
                raise CompileError(
                    "cargo failed with code: %d\n%s" % (
                        e.returncode, e.output.decode("utf-8")))
            except OSError:
                raise DistutilsExecError(
                    "Unable to execute 'cargo' - this package "
                    "requires rust to be installed and "
                    "cargo to be on the PATH")
            else:
                print("Extension '%s' checked" % ext.name)
