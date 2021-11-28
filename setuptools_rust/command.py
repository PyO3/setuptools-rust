from abc import ABC, abstractmethod
from distutils.cmd import Command
from distutils.errors import DistutilsPlatformError
from typing import List

from setuptools.dist import Distribution

from .extension import RustExtension
from .utils import get_rust_version


class RustCommand(Command, ABC):
    """Abstract base class for commands which interact with Rust Extensions."""

    # Types for distutils variables which exist on all commands but seem to be
    # missing from https://github.com/python/typeshed/blob/master/stdlib/distutils/cmd.pyi
    distribution: Distribution
    verbose: int

    def initialize_options(self) -> None:
        self.extensions: List[RustExtension] = []

    def finalize_options(self) -> None:
        self.extensions = [
            ext
            for ext in self.distribution.rust_extensions  # type: ignore[attr-defined]
            if isinstance(ext, RustExtension)
        ]

    def run(self) -> None:
        if not self.extensions:
            return

        all_optional = all(ext.optional for ext in self.extensions)
        try:
            version = get_rust_version()
            if version is None:
                min_version = max(  # type: ignore[type-var]
                    filter(
                        lambda version: version is not None,
                        (ext.get_rust_version() for ext in self.extensions),
                    ),
                    default=None,
                )
                raise DistutilsPlatformError(
                    "can't find Rust compiler\n\n"
                    "If you are using an outdated pip version, it is possible a "
                    "prebuilt wheel is available for this package but pip is not able "
                    "to install from it. Installing from the wheel would avoid the "
                    "need for a Rust compiler.\n\n"
                    "To update pip, run:\n\n"
                    "    pip install --upgrade pip\n\n"
                    "and then retry package installation.\n\n"
                    "If you did intend to build this package from source, try "
                    "installing a Rust compiler from your system package manager and "
                    "ensure it is on the PATH during installation. Alternatively, "
                    "rustup (available at https://rustup.rs) is the recommended way "
                    "to download and update the Rust compiler toolchain."
                    + (
                        f"\n\nThis package requires Rust {min_version}."
                        if min_version is not None
                        else ""
                    )
                )
        except DistutilsPlatformError as e:
            if not all_optional:
                raise
            else:
                print(str(e))
                return

        for ext in self.extensions:
            try:
                rust_version = ext.get_rust_version()
                if rust_version is not None and version not in rust_version:
                    raise DistutilsPlatformError(
                        f"Rust {version} does not match extension requirement {rust_version}"
                    )

                self.run_for_extension(ext)
            except Exception as e:
                if not ext.optional:
                    raise
                else:
                    command_name = self.get_command_name()
                    print(f"{command_name}: optional Rust extension {ext.name} failed")
                    print(str(e))

    @abstractmethod
    def run_for_extension(self, extension: RustExtension) -> None:
        ...
