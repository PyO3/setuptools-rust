from abc import ABC, abstractmethod
from distutils import log
from distutils.cmd import Command
from distutils.errors import DistutilsPlatformError
from typing import List, Optional

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
        extensions: Optional[List[RustExtension]] = getattr(
            self.distribution, "rust_extensions", None
        )
        if extensions is None:
            # extensions is None if the setup.py file did not contain
            # rust_extensions keyword; just no-op if this is the case.
            return

        if not isinstance(extensions, list):
            ty = type(extensions)
            raise ValueError(
                "expected list of RustExtension objects for rust_extensions "
                f"argument to setup(), got `{ty}`"
            )
        for (i, extension) in enumerate(extensions):

            if not isinstance(extension, RustExtension):
                ty = type(extension)
                raise ValueError(
                    "expected RustExtension object for rust_extensions "
                    f"argument to setup(), got `{ty}` at position {i}"
                )
        # Extensions have been verified to be at the correct type
        self.extensions = extensions

    def run(self) -> None:
        if not self.extensions:
            log.info("%s: no rust_extensions defined", self.get_command_name())
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
