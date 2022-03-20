import json
import os
import re
import subprocess
from distutils.errors import DistutilsSetupError
from enum import IntEnum, auto
from typing import Any, Dict, List, NewType, Optional, Union

from semantic_version import SimpleSpec
from typing_extensions import Literal


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
        features: A list of Cargo features to also build.
        rust_version: Minimum Rust compiler version required for this
            extension.
        quiet: Suppress Cargo's output.
        debug: Controls whether ``--debug`` or ``--release`` is passed to
            Cargo. If set to `None` (the default) then build type is
            automatic: ``inplace`` build will be a debug build, ``install``
            and ``wheel`` builds will be release.
        binding: Informs ``setuptools_rust`` which Python binding is in use.
        strip: Strip symbols from final file. Does nothing for debug build.
        script: Generate console script for executable if ``Binding.Exec`` is
            used.
        native: Build extension or executable with ``--target-cpu=native``.
        optional: If it is true, a build failure in the extension will not
            abort the build process, and instead simply not install the failing
            extension.
        py_limited_api: Similar to ``py_limited_api`` on
            ``setuptools.Extension``, this controls whether the built extension
            should be considered compatible with the PEP 384 "limited API".

            - ``'auto'``: the ``--py-limited-api`` option of
              ``setup.py bdist_wheel`` will control whether the extension is
              built as a limited api extension. The corresponding
              ``pyo3/abi3-pyXY`` feature will be set accordingly.
              This is the recommended setting, as it allows
              ``python setup.py install`` to build a version-specific extension
              for best performance.

            - ``True``: the extension is assumed to be compatible with the
              limited abi. You must ensure this is the case (e.g. by setting
              the ``pyo3/abi3`` feature).

            - ``False``: the extension is version-specific.
    """

    def __init__(
        self,
        target: Union[str, Dict[str, str]],
        path: str = "Cargo.toml",
        args: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        rustc_flags: Optional[List[str]] = None,
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
        self.args = args
        self.rustc_flags = rustc_flags
        self.binding = binding
        self.rust_version = rust_version
        self.quiet = quiet
        self.debug = debug
        self.strip = strip
        self.script = script
        self.native = native
        self.optional = optional
        self.py_limited_api = py_limited_api

        if features is None:
            features = []

        self.features = [s.strip() for s in features]

        # get relative path to Cargo manifest file
        path = os.path.relpath(path)
        self.path = path

        self._cargo_metadata: Optional[_CargoMetadata] = None

    def get_lib_name(self) -> str:
        """Parse Cargo.toml to get the name of the shared library."""
        metadata = self._metadata()
        root_key = metadata["resolve"]["root"]
        [pkg] = [p for p in metadata["packages"] if p["id"] == root_key]
        name = pkg["targets"][0]["name"]
        assert isinstance(name, str)
        return re.sub(r"[./\\-]", "_", name)

    def get_rust_version(self) -> Optional[SimpleSpec]:  # type: ignore[no-any-unimported]
        if self.rust_version is None:
            return None
        try:
            return SimpleSpec(self.rust_version)
        except ValueError:
            raise DistutilsSetupError(
                "Can not parse rust compiler version: %s", self.rust_version
            )

    def get_cargo_profile(self) -> Optional[str]:
        args = self.args or []
        try:
            index = args.index("--profile")
            return args[index + 1]
        except ValueError:
            pass
        except IndexError:
            raise DistutilsSetupError("Can not parse cargo profile from %s", args)

        # Handle `--profile=<profile>`
        profile_args = [p for p in args if p.startswith("--profile=")]
        if profile_args:
            profile = profile_args[0].split("=", 1)[1]
            if not profile:
                raise DistutilsSetupError("Can not parse cargo profile from %s", args)
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
            file = os.path.join(dirname, f"{script_name}.py")
            with open(file, "w") as f:
                f.write(_SCRIPT_TEMPLATE.format(executable=repr(executable)))

    def _metadata(self) -> "_CargoMetadata":
        """Returns cargo metedata for this extension package.

        Cached - will only execute cargo on first invocation.
        """
        if self._cargo_metadata is None:
            metadata_command = [
                "cargo",
                "metadata",
                "--manifest-path",
                self.path,
                "--format-version",
                "1",
            ]
            self._cargo_metadata = json.loads(subprocess.check_output(metadata_command))
        return self._cargo_metadata

    def _uses_exec_binding(self) -> bool:
        return self.binding == Binding.Exec


_CargoMetadata = NewType("_CargoMetadata", Dict[str, Any])


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
