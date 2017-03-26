from __future__ import print_function, absolute_import
import sys
import subprocess
from distutils.cmd import Command

from .extension import RustExtension


class clean_rust(Command):
    """ Clean rust extensions. """

    description = "clean rust extensions (compile/link to build directory)"

    def initialize_options(self):
        self.extensions = ()
        self.inplace = False

    def finalize_options(self):
        self.extensions = [ext for ext in self.distribution.rust_extensions
                           if isinstance(ext, RustExtension)]

    def run(self):
        if not self.extensions:
            return

        for ext in self.extensions:
            # build cargo command
            args = (["cargo", "clean", "--manifest-path", ext.path])

            if not ext.quiet:
                print(" ".join(args), file=sys.stderr)

            # Execute cargo command
            try:
                subprocess.check_output(args)
            except:
                pass
