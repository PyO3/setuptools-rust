from __future__ import annotations

import glob
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
from distutils import log
from distutils.errors import (
    CompileError,
    DistutilsExecError,
    DistutilsFileError,
    DistutilsPlatformError,
)
from distutils.sysconfig import get_config_var
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple, cast

import pkg_resources
from setuptools.command.build import build as CommandBuild  # type: ignore[import]
from setuptools.command.build_ext import build_ext as CommandBuildExt
from setuptools.command.build_ext import get_abi3_suffix
from typing_extensions import Literal

from ._utils import format_called_process_error
from .command import RustCommand
from .extension import Binding, RustBin, RustExtension, Strip
from .rustc_info import get_rust_host, get_rust_target_list, get_rustc_cfgs


class build_rust(RustCommand):
    """Command for building Rust crates via cargo."""

    description = "build Rust extensions (compile/link to build directory)"

    user_options = [
        (
            "inplace",
            "i",
            "ignore build-lib and put compiled extensions into the source "
            + "directory alongside your pure Python modules",
        ),
        ("debug", "d", "Force debug to true for all Rust extensions "),
        ("release", "r", "Force debug to false for all Rust extensions "),
        ("qbuild", None, "Force enable quiet option for all Rust extensions "),
        (
            "build-temp",
            "t",
            "directory for temporary files (cargo 'target' directory) ",
        ),
        ("target=", None, "Build for the target triple"),
    ]
    boolean_options = ["inplace", "debug", "release", "qbuild"]

    plat_name: Optional[str] = None

    def initialize_options(self) -> None:
        super().initialize_options()
        self.inplace = None
        self.debug = None
        self.release = None
        self.qbuild = None
        self.build_temp = None
        self.plat_name = None
        self.build_number = None
        self.target = os.getenv("CARGO_BUILD_TARGET")
        self.cargo = os.getenv("CARGO", "cargo")

    def finalize_options(self) -> None:
        super().finalize_options()

        self.data_dir = self.get_data_dir()

        if self.plat_name is None:
            self.plat_name = cast(  # type: ignore[no-any-unimported]
                CommandBuild, self.get_finalized_command("build")
            ).plat_name
            assert isinstance(self.plat_name, str)

        # Inherit settings from the `build_ext` command
        self.set_undefined_options(
            "build_ext",
            ("build_temp", "build_temp"),
            ("debug", "debug"),
            ("inplace", "inplace"),
        )

        if self.build_number is not None and not self.build_number[:1].isdigit():
            raise ValueError("Build tag (build-number) must start with a digit.")

    def get_data_dir(self) -> str:
        components = (
            pkg_resources.safe_name(self.distribution.get_name()).replace("-", "_"),  # type: ignore[attr-defined]
            pkg_resources.safe_version(self.distribution.get_version()).replace("-", "_"),  # type: ignore[attr-defined]
        )
        if self.build_number:
            components += (self.build_number,)
        return "-".join(components) + ".data"

    def run_for_extension(self, ext: RustExtension) -> None:
        assert self.plat_name is not None

        arch_flags = os.getenv("ARCHFLAGS")
        universal2 = False
        if self.plat_name.startswith("macosx-") and arch_flags:
            universal2 = "x86_64" in arch_flags and "arm64" in arch_flags
            if not universal2 and not self.target:
                if "arm64" in arch_flags:
                    self.target = "aarch64-apple-darwin"
                elif "x86_64" in arch_flags:
                    self.target = "x86_64-apple-darwin"

        if universal2:
            arm64_dylib_paths = self.build_extension(ext, "aarch64-apple-darwin")
            x86_64_dylib_paths = self.build_extension(ext, "x86_64-apple-darwin")
            dylib_paths = []
            for (target_fname, arm64_dylib), (_, x86_64_dylib) in zip(
                arm64_dylib_paths, x86_64_dylib_paths
            ):
                fat_dylib_path = arm64_dylib.replace("aarch64-apple-darwin/", "")
                create_universal2_binary(fat_dylib_path, [arm64_dylib, x86_64_dylib])
                dylib_paths.append(_BuiltModule(target_fname, fat_dylib_path))
        else:
            dylib_paths = self.build_extension(ext, self.target)
        self.install_extension(ext, dylib_paths)

    def build_extension(
        self, ext: RustExtension, forced_target_triple: Optional[str] = None
    ) -> List["_BuiltModule"]:

        target_triple = self._detect_rust_target(forced_target_triple)
        rustc_cfgs = get_rustc_cfgs(target_triple)

        env = _prepare_build_environment()

        if not os.path.exists(ext.path):
            raise DistutilsFileError(
                f"can't find Rust extension project file: {ext.path}"
            )

        quiet = self.qbuild or ext.quiet
        debug = self._is_debug_build(ext)

        cargo_args = self._cargo_args(
            ext=ext, target_triple=target_triple, release=not debug, quiet=quiet
        )

        rustflags = []

        if ext._uses_exec_binding():
            command = [
                self.cargo,
                "build",
                "--manifest-path",
                ext.path,
                "--message-format=json-render-diagnostics",
                *cargo_args,
            ]

        else:
            rustc_args = [
                "--crate-type",
                "cdylib",
                *ext.rustc_flags,
            ]

            # OSX requires special linker arguments
            if rustc_cfgs.get("target_os") == "macos":
                ext_basename = os.path.basename(self.get_dylib_ext_path(ext, ext.name))
                rustc_args.extend(
                    [
                        "-C",
                        f"link-args=-undefined dynamic_lookup -Wl,-install_name,@rpath/{ext_basename}",
                    ]
                )

            # Tell musl targets not to statically link libc. See
            # https://github.com/rust-lang/rust/issues/59302 for details.
            if rustc_cfgs.get("target_env") == "musl":
                # This must go in the env otherwise rustc will refuse to build
                # the cdylib, see https://github.com/rust-lang/cargo/issues/10143
                rustflags.append("-Ctarget-feature=-crt-static")

            elif (rustc_cfgs.get("target_arch"), rustc_cfgs.get("target_os")) == (
                "wasm32",
                "emscripten",
            ):
                rustc_args.extend(["-C", f"link-args=-sSIDE_MODULE=2 -sWASM_BIGINT"])

            command = [
                self.cargo,
                "rustc",
                "--lib",
                "--message-format=json-render-diagnostics",
                "--manifest-path",
                ext.path,
                *cargo_args,
                "--",
                *rustc_args,
            ]

        if rustflags:
            existing_rustflags = env.get("RUSTFLAGS")
            if existing_rustflags is not None:
                rustflags.append(existing_rustflags)
            new_rustflags = " ".join(rustflags)
            env["RUSTFLAGS"] = new_rustflags

            # print RUSTFLAGS being added before the command
            if not quiet:
                print(f"[RUSTFLAGS={new_rustflags}]", end=" ", file=sys.stderr)

        if not quiet:
            print(" ".join(command), file=sys.stderr)

        # Execute cargo
        try:
            # If quiet, capture all output and only show it in the exception
            # If not quiet, forward all cargo output to stderr
            stderr = subprocess.PIPE if quiet else None
            cargo_messages = subprocess.check_output(
                command,
                env=env,
                stderr=stderr,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            # Don't include stdout in the formatted error as it is a huge dump
            # of cargo json lines which aren't helpful for the end user.
            raise CompileError(format_called_process_error(e, include_stdout=False))

        except OSError:
            raise DistutilsExecError(
                "Unable to execute 'cargo' - this package "
                "requires Rust to be installed and cargo to be on the PATH"
            )

        # Find the shared library that cargo hopefully produced and copy
        # it into the build directory as if it were produced by build_ext.

        dylib_paths = []
        package_id = ext.metadata(quiet=quiet)["resolve"]["root"]

        if ext._uses_exec_binding():
            # Find artifact from cargo messages
            artifacts = _find_cargo_artifacts(
                cargo_messages.splitlines(),
                package_id=package_id,
                kinds={"bin"},
            )
            for name, dest in ext.target.items():
                if not name:
                    name = dest.split(".")[-1]

                try:
                    artifact_path = next(
                        artifact
                        for artifact in artifacts
                        if Path(artifact).with_suffix("").name == name
                    )
                except StopIteration:
                    raise DistutilsExecError(
                        f"Rust build failed; unable to locate executable '{name}'"
                    )

                if os.environ.get("CARGO") == "cross":
                    artifact_path = _replace_cross_target_dir(
                        artifact_path, ext, quiet=quiet
                    )

                dylib_paths.append(_BuiltModule(dest, artifact_path))
        else:
            # Find artifact from cargo messages
            artifacts = _find_cargo_artifacts(
                cargo_messages.splitlines(),
                package_id=package_id,
                kinds={"cdylib", "dylib"},
            )
            if len(artifacts) == 0:
                raise DistutilsExecError(
                    "Rust build failed; unable to find any cdylib or dylib build artifacts"
                )
            elif len(artifacts) > 1:
                raise DistutilsExecError(
                    f"Rust build failed; expected only one cdylib or dylib build artifact but found {artifacts}"
                )

            artifact_path = artifacts[0]

            if os.environ.get("CARGO") == "cross":
                artifact_path = _replace_cross_target_dir(
                    artifact_path, ext, quiet=quiet
                )

            # guaranteed to be just one element after checks above
            dylib_paths.append(_BuiltModule(ext.name, artifact_path))
        return dylib_paths

    def install_extension(
        self, ext: RustExtension, dylib_paths: List["_BuiltModule"]
    ) -> None:
        debug_build = ext.debug if ext.debug is not None else self.inplace
        debug_build = self.debug if self.debug is not None else debug_build
        if self.release:
            debug_build = False

        # Ask build_ext where the shared library would go if it had built it,
        # then copy it there.
        build_ext = cast(CommandBuildExt, self.get_finalized_command("build_ext"))
        build_ext.inplace = self.inplace

        for module_name, dylib_path in dylib_paths:
            if not module_name:
                module_name = os.path.basename(
                    os.path.splitext(os.path.basename(dylib_path)[3:])[0]
                )

            if ext._uses_exec_binding():
                ext_path = build_ext.get_ext_fullpath(module_name)
                # remove extensions
                ext_path, _, _ = _split_platform_and_extension(ext_path)

                # Add expected extension
                exe = sysconfig.get_config_var("EXE")
                if exe is not None:
                    ext_path += exe

                os.makedirs(os.path.dirname(ext_path), exist_ok=True)
                if isinstance(ext, RustBin):
                    executable_name = module_name
                    if exe is not None:
                        executable_name += exe
                    scripts_dir = os.path.join(
                        build_ext.build_lib, self.data_dir, "scripts"
                    )
                    os.makedirs(scripts_dir, exist_ok=True)
                    ext_path = os.path.join(scripts_dir, executable_name)
                else:
                    ext.install_script(module_name.split(".")[-1], ext_path)
            else:
                ext_path = self.get_dylib_ext_path(ext, module_name)
                os.makedirs(os.path.dirname(ext_path), exist_ok=True)

            log.info("Copying rust artifact from %s to %s", dylib_path, ext_path)
            shutil.copyfile(dylib_path, ext_path)

            if sys.platform != "win32" and not debug_build:
                args = []
                if ext.strip == Strip.All:
                    args.append("-x")
                elif ext.strip == Strip.Debug:
                    args.append("-S")

                if args:
                    args.insert(0, "strip")
                    args.append(ext_path)
                    try:
                        output = subprocess.check_output(args)
                    except subprocess.CalledProcessError:
                        pass

            # executables, win32(cygwin)-dll's, and shared libraries on
            # Unix-like operating systems need X bits
            mode = os.stat(ext_path).st_mode
            mode |= (mode & 0o444) >> 2  # copy R bits to X
            os.chmod(ext_path, mode)

    def get_dylib_ext_path(self, ext: RustExtension, target_fname: str) -> str:
        assert self.plat_name is not None
        build_ext = cast(CommandBuildExt, self.get_finalized_command("build_ext"))

        ext_path: str = build_ext.get_ext_fullpath(target_fname)

        if _is_py_limited_api(ext.py_limited_api, self._py_limited_api()):
            abi3_suffix = get_abi3_suffix()
            if abi3_suffix is not None:
                so_ext = get_config_var("EXT_SUFFIX")
                assert isinstance(so_ext, str)
                ext_path = ext_path[: -len(so_ext)] + get_abi3_suffix()

        if ".abi3." in ext_path:
            return ext_path
        # Examples: linux_x86_64, linux_i686, manylinux2014_aarch64, manylinux_2_24_armv7l
        plat_name = self.plat_name.lower().replace("-", "_").replace(".", "_")
        if not plat_name.startswith(("linux", "manylinux")):
            return ext_path

        arch_parts = []
        arch_found = False
        for item in plat_name.split("_"):
            if item.startswith(("linux", "manylinux")):
                continue
            if item.isdigit() and not arch_found:
                # manylinux_2_24_armv7l arch should be armv7l
                continue
            arch_found = True
            arch_parts.append(item)
        target_arch = "_".join(arch_parts)
        host_platform = sysconfig.get_platform()
        host_arch = host_platform.rsplit("-", 1)[1]
        # Remove incorrect platform tag if we are cross compiling
        if target_arch and host_arch != target_arch:
            ext_path, _, extension = _split_platform_and_extension(ext_path)
            # rust.so, removed platform tag
            ext_path += extension
        return ext_path

    def _py_limited_api(self) -> _PyLimitedApi:
        bdist_wheel = self.distribution.get_command_obj("bdist_wheel", create=False)

        if bdist_wheel is None:
            # wheel package is not installed, not building a limited-api wheel
            return False
        else:
            from wheel.bdist_wheel import bdist_wheel as CommandBdistWheel

            bdist_wheel_command = cast(CommandBdistWheel, bdist_wheel)  # type: ignore[no-any-unimported]
            bdist_wheel_command.ensure_finalized()
            return cast(_PyLimitedApi, bdist_wheel_command.py_limited_api)

    def _detect_rust_target(
        self, forced_target_triple: Optional[str] = None
    ) -> Optional[str]:
        assert self.plat_name is not None
        if forced_target_triple is not None:
            # Automatic target detection can be overridden via the CARGO_BUILD_TARGET
            # environment variable or --target command line option
            return forced_target_triple

        # Determine local rust target which needs to be "forced" if necessary
        local_rust_target = _adjusted_local_rust_target(self.plat_name)

        # Match cargo's behaviour of not using an explicit target if the
        # target we're compiling for is the host
        if (
            local_rust_target is not None
            # check for None first to avoid calling to rustc if not needed
            and local_rust_target != get_rust_host()
        ):
            return local_rust_target

        return None

    def _is_debug_build(self, ext: RustExtension) -> bool:
        if self.release:
            return False
        elif self.debug is not None:
            return self.debug
        elif ext.debug is not None:
            return ext.debug
        else:
            return bool(self.inplace)

    def _cargo_args(
        self,
        ext: RustExtension,
        target_triple: Optional[str],
        release: bool,
        quiet: bool,
    ) -> List[str]:
        args = []
        if target_triple is not None:
            args.extend(["--target", target_triple])

        if release:
            profile = ext.get_cargo_profile()
            if not profile:
                args.append("--release")

        if quiet:
            args.append("-q")

        elif self.verbose:
            # cargo only have -vv
            verbose_level = "v" * min(self.verbose, 2)
            args.append(f"-{verbose_level}")

        features = {
            *ext.features,
            *_binding_features(ext, py_limited_api=self._py_limited_api()),
        }

        if features:
            args.extend(["--features", " ".join(features)])

        if ext.args is not None:
            args.extend(ext.args)

        if ext.cargo_manifest_args is not None:
            args.extend(ext.cargo_manifest_args)

        return args


def create_universal2_binary(output_path: str, input_paths: List[str]) -> None:
    # Try lipo first
    command = ["lipo", "-create", "-output", output_path, *input_paths]
    try:
        subprocess.check_output(command, text=True)
    except subprocess.CalledProcessError as e:
        output = e.output
        raise CompileError("lipo failed with code: %d\n%s" % (e.returncode, output))
    except OSError:
        # lipo not found, try using the fat-macho library
        try:
            from fat_macho import FatWriter
        except ImportError:
            raise DistutilsExecError(
                "failed to locate `lipo` or import `fat_macho.FatWriter`. "
                "Try installing with `pip install fat-macho` "
            )
        fat = FatWriter()
        for input_path in input_paths:
            with open(input_path, "rb") as f:
                fat.add(f.read())
        fat.write_to(output_path)


class _BuiltModule(NamedTuple):
    """
    Attributes:
        - module_name: dotted python import path of the module
        - path: the location the module has been installed at
    """

    module_name: str
    path: str


def _replace_vendor_with_unknown(target: str) -> Optional[str]:
    """Replaces vendor in the target triple with unknown.

    Returns None if the target is not made of 4 parts.
    """
    components = target.split("-")
    if len(components) != 4:
        return None
    components[1] = "unknown"
    return "-".join(components)


def _prepare_build_environment() -> Dict[str, str]:
    """Prepares environment variables to use when executing cargo build."""

    # Make sure that if pythonXX-sys is used, it builds against the current
    # executing python interpreter.
    bindir = os.path.dirname(sys.executable)

    env = os.environ.copy()
    env.update(
        {
            # disables rust's pkg-config seeking for specified packages,
            # which causes pythonXX-sys to fall back to detecting the
            # interpreter from the path.
            "PATH": os.path.join(bindir, os.environ.get("PATH", "")),
            "PYTHON_SYS_EXECUTABLE": os.environ.get(
                "PYTHON_SYS_EXECUTABLE", sys.executable
            ),
            "PYO3_PYTHON": os.environ.get("PYO3_PYTHON", sys.executable),
        }
    )
    return env


def _is_py_limited_api(
    ext_setting: Literal["auto", True, False],
    wheel_setting: Optional[_PyLimitedApi],
) -> bool:
    """Returns whether this extension is being built for the limited api.

    >>> _is_py_limited_api("auto", None)
    False

    >>> _is_py_limited_api("auto", True)
    True

    >>> _is_py_limited_api(True, False)
    True

    >>> _is_py_limited_api(False, True)
    False
    """

    # If the extension explicitly states to use py_limited_api or not, use that.
    if ext_setting != "auto":
        return ext_setting

    # "auto" setting - use whether the bdist_wheel option is truthy.
    return bool(wheel_setting)


def _binding_features(
    ext: RustExtension,
    py_limited_api: _PyLimitedApi,
) -> Set[str]:
    if ext.binding in (Binding.NoBinding, Binding.Exec):
        return set()
    elif ext.binding is Binding.PyO3:
        features = {"pyo3/extension-module"}
        if ext.py_limited_api == "auto":
            if isinstance(py_limited_api, str):
                python_version = py_limited_api[2:]
                features.add(f"pyo3/abi3-py{python_version}")
            elif py_limited_api:
                features.add(f"pyo3/abi3")
        return features
    elif ext.binding is Binding.RustCPython:
        return {"cpython/python3-sys", "cpython/extension-module"}
    else:
        raise DistutilsPlatformError(f"unknown Rust binding: '{ext.binding}'")


_PyLimitedApi = Literal["cp37", "cp38", "cp39", "cp310", "cp311", "cp312", True, False]


def _adjusted_local_rust_target(plat_name: str) -> Optional[str]:
    """Returns the local rust target for the given `plat_name`, if it is
    necessary to 'force' a specific target for correctness."""

    # If we are on a 64-bit machine, but running a 32-bit Python, then
    # we'll target a 32-bit Rust build.
    if plat_name == "win32":
        if get_rustc_cfgs(None).get("target_env") == "gnu":
            return "i686-pc-windows-gnu"
        else:
            return "i686-pc-windows-msvc"
    elif plat_name == "win-amd64":
        if get_rustc_cfgs(None).get("target_env") == "gnu":
            return "x86_64-pc-windows-gnu"
        else:
            return "x86_64-pc-windows-msvc"
    elif plat_name.startswith("macosx-") and platform.machine() == "x86_64":
        # x86_64 or arm64 macOS targeting x86_64
        return "x86_64-apple-darwin"

    return None


def _split_platform_and_extension(ext_path: str) -> Tuple[str, str, str]:
    """Splits an extension path into a tuple (ext_path, plat_tag, extension).

    >>> _split_platform_and_extension("foo/bar.platform.so")
    ('foo/bar', '.platform', '.so')
    """

    # rust.cpython-38-x86_64-linux-gnu.so to (rust.cpython-38-x86_64-linux-gnu, .so)
    ext_path, extension = os.path.splitext(ext_path)
    # rust.cpython-38-x86_64-linux-gnu to (rust, .cpython-38-x86_64-linux-gnu)
    ext_path, platform_tag = os.path.splitext(ext_path)
    return (ext_path, platform_tag, extension)


def _find_cargo_artifacts(
    cargo_messages: List[str],
    *,
    package_id: str,
    kinds: Set[str],
) -> List[str]:
    """Identifies cargo artifacts built for the given `package_id` from the
    provided cargo_messages.

    >>> _find_cargo_artifacts(
    ...    [
    ...        '{"some_irrelevant_message": []}',
    ...        '{"reason":"compiler-artifact","package_id":"some_id","target":{"kind":["cdylib"]},"filenames":["/some/path/baz.so"]}',
    ...        '{"reason":"compiler-artifact","package_id":"some_id","target":{"kind":["dylib", "rlib"]},"filenames":["/file/two/baz.dylib", "/file/two/baz.rlib"]}',
    ...        '{"reason":"compiler-artifact","package_id":"some_other_id","target":{"kind":["cdylib"]},"filenames":["/not/this.so"]}',
    ...    ],
    ...    package_id="some_id",
    ...    kinds={"cdylib", "dylib"},
    ... )
    ['/some/path/baz.so', '/file/two/baz.dylib']
    >>> _find_cargo_artifacts(
    ...    [
    ...        '{"some_irrelevant_message": []}',
    ...        '{"reason":"compiler-artifact","package_id":"some_id","target":{"kind":["cdylib"]},"filenames":["/some/path/baz.so"]}',
    ...        '{"reason":"compiler-artifact","package_id":"some_id","target":{"kind":["cdylib", "rlib"]},"filenames":["/file/two/baz.dylib", "/file/two/baz.rlib"]}',
    ...        '{"reason":"compiler-artifact","package_id":"some_other_id","target":{"kind":["cdylib"]},"filenames":["/not/this.so"]}',
    ...    ],
    ...    package_id="some_id",
    ...    kinds={"rlib"},
    ... )
    ['/file/two/baz.rlib']
    """
    artifacts = []
    for message in cargo_messages:
        # only bother parsing messages that look like a match
        if "compiler-artifact" in message and package_id in message:
            parsed = json.loads(message)
            # verify the message is correct
            if (
                parsed.get("reason") == "compiler-artifact"
                and parsed.get("package_id") == package_id
            ):
                for artifact_kind, filename in zip(
                    parsed["target"]["kind"], parsed["filenames"]
                ):
                    if artifact_kind in kinds:
                        artifacts.append(filename)
    return artifacts


def _replace_cross_target_dir(path: str, ext: RustExtension, *, quiet: bool) -> str:
    """Replaces target director from `cross` docker build with the correct
    local path.

    Cross artifact messages and metadata contain paths from inside the
    dockerfile; invoking `cargo metadata` we can work out the correct local
    target directory.
    """
    cross_target_dir = ext._metadata(cargo="cross", quiet=quiet)["target_directory"]
    local_target_dir = ext._metadata(cargo="cargo", quiet=quiet)["target_directory"]
    return path.replace(cross_target_dir, local_target_dir)
