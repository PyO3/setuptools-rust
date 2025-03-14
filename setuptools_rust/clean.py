import sys

from setuptools_rust._utils import check_subprocess_output

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
            check_subprocess_output(args, env=ext.env)
        except Exception:
            pass
