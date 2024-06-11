from __future__ import annotations

import json
import os
import re
import subprocess
import warnings
from setuptools.errors import SetupError
from enum import IntEnum, auto
from functools import lru_cache
from typing import (
    Any,
    Dict,
    List,
    Literal,
    NewType,
    Optional,
    Sequence,
    TYPE_CHECKING,
    Union,
    cast,
)

if TYPE_CHECKING:
    from semantic_version import SimpleSpec

from ._utils import format_called_process_error


class Binding(IntEnum):
    """
    Enumeration of possible Rust binding types supported by ``setuptools-rust``.

    Attributes:
        PyO3: This is an extension built using
            `PyO3 <https://github.com/pyo3/pyo3>`_.
        RustCPython: This is an extension built using
            `rust-cpython <https://github.com/dgrunwald/rust_cpython>`_.
        NoBinding: Bring your own bindings for the extension.
        Exec: Build an executable instead of an extension.
    """

    PyO3 = auto()
    RustCPython = auto()
    NoBinding = auto()
    Exec = auto()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class Strip(IntEnum):
    """
    Enumeration of modes for stripping symbols from the built extension.

    Attributes:
        No: Do not strip symbols.
        Debug: Strip debug symbols.
        All: Strip all symbols.
    """

    No = auto()
    Debug = auto()
    All = auto()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class RustExtension:
    """Used to define a rust extension module and its build configuration.

    Args:
        target: The full Python dotted name of the extension, including any
            packages, i.e *not* a filename or pathname. It is possible to
            specify multiple binaries, if extension uses ``Binding.Exec``
            binding mode. In that case first argument has to be dictionary.
            Keys of the dictionary correspond to the rust binary names and
            values are the full dotted name to place the executable inside
            the python package. To install executables with kebab-case names,
            the final part of the dotted name can be in kebab-case. For
            example, `hello_world.hello-world` will install an executable
            named `hello-world`.
        path: Path to the ``Cargo.toml`` manifest file.
        args: A list of extra arguments to be passed to Cargo. For example,
            ``args=["--no-default-features"]`` will disable the default
            features listed in ``Cargo.toml``.
        cargo_manifest_args: A list of extra arguments to be passed to Cargo.
            These arguments will be passed to every ``cargo`` command, not just
            ``cargo build``. For valid options, see
            `the Cargo Book <https://doc.rust-lang.org/cargo/commands/cargo-build.html#manifest-options>`_.
            For example, ``cargo_manifest_args=["--locked"]`` will require
            ``Cargo.lock`` files are up to date.
        features: Cargo `--features` to add to the build.
        rustc_flags: A list of additional flags passed to `cargo rustc`. These
            only affect the final artifact, usually you should set the
            `RUSTFLAGS` environment variable.
        rust_version: Minimum Rust compiler version required for this
            extension.
        quiet: Suppress Cargo's output.
        debug: Controls whether ``--debug`` or ``--release`` is passed to
            Cargo. If set to `None` (the default) then build type is
            automatic: ``inplace`` build will be a debug build, ``install``
            and ``wheel`` builds will be release.
        binding: Informs ``setuptools_rust`` which Python binding is in use.
        strip: Strip symbols from final file. Does nothing for debug build.
        native: Build extension or executable with ``-Ctarget-cpu=native``
            (deprecated, set environment variable RUSTFLAGS=-Ctarget-cpu=native).
        script: Generate console script for executable if ``Binding.Exec`` is
            used (deprecated, just use ``RustBin`` instead).
        optional: If it is true, a build failure in the extension will not
            abort the build process, and instead simply not install the failing
            extension.
        py_limited_api: Deprecated.
    """

    def __init__(
        self,
        target: Union[str, Dict[str, str]],
        path: str = "Cargo.toml",
        args: Optional[Sequence[str]] = (),
        cargo_manifest_args: Optional[Sequence[str]] = (),
        features: Optional[Sequence[str]] = (),
        rustc_flags: Optional[Sequence[str]] = (),
        rust_version: Optional[str] = None,
        quiet: bool = False,
        debug: Optional[bool] = None,
        binding: Binding = Binding.PyO3,
        strip: Strip = Strip.No,
        script: bool = False,
        native: bool = False,
        optional: bool = False,
        py_limited_api: Literal["auto", True, False] = "auto",
    ):
        if isinstance(target, dict):
            name = "; ".join("%s=%s" % (key, val) for key, val in target.items())
        else:
            name = target
            target = {"": target}

        self.name = name
        self.target = target
        self.path = os.path.relpath(path)  # relative path to Cargo manifest file
        self.args = tuple(args or ())
        self.cargo_manifest_args = tuple(cargo_manifest_args or ())
        self.features = tuple(features or ())
        self.rustc_flags = tuple(rustc_flags or ())
        self.rust_version = rust_version
        self.quiet = quiet
        self.debug = debug
        self.binding = binding
        self.strip = strip
        self.script = script
        self.optional = optional
        self.py_limited_api = py_limited_api

        if native:
            warnings.warn(
                "`native` is deprecated, set RUSTFLAGS=-Ctarget-cpu=native instead.",
                DeprecationWarning,
            )
            # match old behaviour of only setting flag for top-level crate;
            # setting for `rustflags` is strictly better
            self.rustc_flags = (*self.rustc_flags, "-Ctarget-cpu=native")

        if binding == Binding.Exec and script:
            warnings.warn(
                "`Binding.Exec` with `script=True` is deprecated, use `RustBin` instead.",
                DeprecationWarning,
            )

        if self.py_limited_api != "auto":
            warnings.warn(
                "`RustExtension.py_limited_api` is deprecated, use [bdist_wheel] configuration "
                "in `setup.cfg` or `DIST_EXTRA_CONFIG` to build abi3 wheels.",
                DeprecationWarning,
            )

    def get_lib_name(self, *, quiet: bool) -> str:
        """Parse Cargo.toml to get the name of the shared library."""
        metadata = self.metadata(quiet=quiet)
        root_key = metadata["resolve"]["root"]
        [pkg] = [p for p in metadata["packages"] if p["id"] == root_key]
        name = pkg["targets"][0]["name"]
        assert isinstance(name, str)
        return re.sub(r"[./\\-]", "_", name)

    def get_rust_version(self) -> Optional[SimpleSpec]:  # type: ignore[no-any-unimported]
        if self.rust_version is None:
            return None
        try:
            from semantic_version import SimpleSpec

            return SimpleSpec(self.rust_version)
        except ValueError:
            raise SetupError(
                "Can not parse rust compiler version: %s", self.rust_version
            )

    def get_cargo_profile(self) -> Optional[str]:
        try:
            index = self.args.index("--profile")
            return self.args[index + 1]
        except ValueError:
            pass
        except IndexError:
            raise SetupError("Can not parse cargo profile from %s", self.args)

        # Handle `--profile=<profile>`
        profile_args = [p for p in self.args if p.startswith("--profile=")]
        if profile_args:
            profile = profile_args[0].split("=", 1)[1]
            if not profile:
                raise SetupError("Can not parse cargo profile from %s", self.args)
            return profile
        else:
            return None

    def entry_points(self) -> List[str]:
        entry_points = []
        if self.script and self.binding == Binding.Exec:
            for executable, mod in self.target.items():
                base_mod, name = mod.rsplit(".")
                script = "%s=%s.%s:run" % (name, base_mod, _script_name(executable))
                entry_points.append(script)

        return entry_points

    def install_script(self, module_name: str, exe_path: str) -> None:
        if self.script and self.binding == Binding.Exec:
            dirname, executable = os.path.split(exe_path)
            script_name = _script_name(module_name)
            os.makedirs(dirname, exist_ok=True)
            file = os.path.join(dirname, f"{script_name}.py")
            with open(file, "w") as f:
                f.write(_SCRIPT_TEMPLATE.format(executable=repr(executable)))

    def metadata(self, *, quiet: bool) -> "CargoMetadata":
        """Returns cargo metadata for this extension package.

        Cached - will only execute cargo on first invocation.
        """

        return self._metadata(os.environ.get("CARGO", "cargo"), quiet)

    @lru_cache()
    def _metadata(self, cargo: str, quiet: bool) -> "CargoMetadata":
        metadata_command = [
            cargo,
            "metadata",
            "--manifest-path",
            self.path,
            "--format-version",
            "1",
        ]
        if self.cargo_manifest_args:
            metadata_command.extend(self.cargo_manifest_args)

        try:
            # If quiet, capture stderr and only show it on exceptions
            # If not quiet, let stderr be inherited
            stderr = subprocess.PIPE if quiet else None
            payload = subprocess.check_output(
                metadata_command, stderr=stderr, encoding="latin-1"
            )
        except subprocess.CalledProcessError as e:
            raise SetupError(format_called_process_error(e))
        try:
            return cast(CargoMetadata, json.loads(payload))
        except json.decoder.JSONDecodeError as e:
            raise SetupError(
                f"""
                Error parsing output of cargo metadata as json; received:
                {payload}
                """
            ) from e

    def _uses_exec_binding(self) -> bool:
        return self.binding == Binding.Exec


class RustBin(RustExtension):
    """Used to define a Rust binary and its build configuration.

    Args:
        target: Rust binary target name.
        path: Path to the ``Cargo.toml`` manifest file.
        args: A list of extra arguments to be passed to Cargo. For example,
            ``args=["--no-default-features"]`` will disable the default
            features listed in ``Cargo.toml``.
        cargo_manifest_args: A list of extra arguments to be passed to Cargo.
            These arguments will be passed to every ``cargo`` command, not just
            ``cargo build``. For valid options, see
            `the Cargo Book <https://doc.rust-lang.org/cargo/commands/cargo-build.html#manifest-options>`_.
            For example, ``cargo_manifest_args=["--locked"]`` will require
            ``Cargo.lock`` files are up to date.
        features: Cargo `--features` to add to the build.
        rust_version: Minimum Rust compiler version required for this bin.
        quiet: Suppress Cargo's output.
        debug: Controls whether ``--debug`` or ``--release`` is passed to
            Cargo. If set to `None` (the default) then build type is
            automatic: ``inplace`` build will be a debug build, ``install``
            and ``wheel`` builds will be release.
        strip: Strip symbols from final file. Does nothing for debug build.
        optional: If it is true, a build failure in the bin will not
            abort the build process, and instead simply not install the failing
            bin.
    """

    def __init__(
        self,
        target: Union[str, Dict[str, str]],
        path: str = "Cargo.toml",
        args: Optional[Sequence[str]] = (),
        cargo_manifest_args: Optional[Sequence[str]] = (),
        features: Optional[Sequence[str]] = (),
        rust_version: Optional[str] = None,
        quiet: bool = False,
        debug: Optional[bool] = None,
        strip: Strip = Strip.No,
        optional: bool = False,
    ):
        super().__init__(
            target=target,
            path=path,
            args=args,
            cargo_manifest_args=cargo_manifest_args,
            features=features,
            rust_version=rust_version,
            quiet=quiet,
            debug=debug,
            binding=Binding.Exec,
            optional=optional,
            strip=strip,
            py_limited_api=False,
        )

    def entry_points(self) -> List[str]:
        return []


CargoMetadata = NewType("CargoMetadata", Dict[str, Any])


def _script_name(executable: str) -> str:
    """Generates the name of the installed Python script for an executable.

    Because Python modules must be snake_case, this generated script name will
    replace `-` with `_`.

    >>> _script_name("hello-world")
    '_gen_hello_world'

    >>> _script_name("foo_bar")
    '_gen_foo_bar'

    >>> _script_name("_gen_foo_bar")
    '_gen__gen_foo_bar'
    """
    script = executable.replace("-", "_")
    return f"_gen_{script}"


_SCRIPT_TEMPLATE = """
import os
import sys

def run():
    path = os.path.split(__file__)[0]
    file = os.path.join(path, {executable})
    if os.path.isfile(file):
        os.execv(file, sys.argv)
    else:
        raise RuntimeError("can't find " + file)
"""
