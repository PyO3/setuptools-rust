import subprocess
import sys

from .command import RustCommand
from .extension import RustExtension


class clean_rust(RustCommand):
    """Clean Rust extensions."""

    description = "clean Rust extensions (compile/link to build directory)"

    def initialize_options(self) -> None:
        super().initialize_options()
        self.inplace = False

    def run_for_extension(self, ext: RustExtension) -> None:
        # build cargo command
        args = ["cargo", "clean", "--manifest-path", ext.path]
        if ext.cargo_manifest_args:
            args.extend(ext.cargo_manifest_args)

        if not ext.quiet:
            print(" ".join(args), file=sys.stderr)

        # Execute cargo command
        try:
            subprocess.check_output(args)
        except Exception:
            pass
