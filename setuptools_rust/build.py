from __future__ import annotations

import collections
import enum
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import logging
import warnings
from setuptools.errors import (
    CompileError,
    ExecError,
    FileError,
    PlatformError,
)
from sysconfig import get_config_var
from pathlib import Path
from typing import Dict, List, Literal, NamedTuple, Optional, Set, Tuple, Union, cast

from setuptools import Distribution
from setuptools.command.build_ext import build_ext as CommandBuildExt
from setuptools.command.build_ext import get_abi3_suffix
from setuptools.command.build_py import build_py as setuptools_build_py
from setuptools.command.install_scripts import install_scripts as CommandInstallScripts

from ._utils import check_subprocess_output, format_called_process_error, Env
from .command import RustCommand
from .extension import Binding, RustBin, RustExtension, Strip
from .rustc_info import (
    get_rust_host,
    get_rust_version,
    get_rustc_cfgs,
)

logger = logging.getLogger(__name__)


try:
    from setuptools.command.bdist_wheel import bdist_wheel as CommandBdistWheel
except ImportError:  # old version of setuptools
    try:
        from wheel.bdist_wheel import bdist_wheel as CommandBdistWheel  # type: ignore[no-redef]
    except ImportError:
        from setuptools import Command as CommandBdistWheel  # type: ignore[assignment]


def _check_cargo_supports_crate_type_option(env: Optional[Env]) -> bool:
    version = get_rust_version(env)

    if version is None:
        return False

    return version.major > 1 or (version.major == 1 and version.minor >= 64)  # type: ignore


_UNIVERSAL2_TARGETS = ("aarch64-apple-darwin", "x86_64-apple-darwin")


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

    inplace: bool = False
    debug: bool = False
    release: bool = False
    qbuild: bool = False

    plat_name: Optional[str] = None
    build_temp: Optional[str] = None

    def initialize_options(self) -> None:
        super().initialize_options()
        self.target = os.getenv("CARGO_BUILD_TARGET", _Platform.CARGO_DEFAULT)
        self.cargo = os.getenv("CARGO", "cargo")

    def finalize_options(self) -> None:
        super().finalize_options()
        if self.target is None:
            self.target = _Platform.CARGO_DEFAULT
        # Inherit settings from the `build` and `build_ext` commands
        self.set_undefined_options(
            "build",
            ("plat_name", "plat_name"),
        )

        # Inherit settings from the `build_ext` command
        self.set_undefined_options(
            "build_ext",
            ("build_temp", "build_temp"),
            ("debug", "debug"),
            ("inplace", "inplace"),
        )

        if self.build_temp is not None:
            warnings.warn(
                "`--build-temp` argument does nothing for Rust extensions, set `CARGO_TARGET_DIR` instead.",
                DeprecationWarning,
            )

    def run_for_extension(self, ext: RustExtension) -> None:
        assert self.plat_name is not None
        if self.target is _Platform.CARGO_DEFAULT:
            self.target = _override_cargo_default_target(self.plat_name, ext.env)
        dylib_paths, artifact_dirs = self.build_extension(ext)
        self.install_extension(ext, dylib_paths, artifact_dirs)

    def build_extension(
        self, ext: RustExtension
    ) -> Tuple[List["_BuiltModule"], List[Path]]:
        env = _prepare_build_environment(ext.env, ext)

        if not os.path.exists(ext.path):
            raise FileError(
                f"can't find manifest for Rust extension `{ext.name}` at path `{ext.path}`"
            )

        quiet = self.qbuild or ext.quiet
        debug = self._is_debug_build(ext)
        use_cargo_crate_type = _check_cargo_supports_crate_type_option(ext.env)

        package_id = ext.metadata(quiet=quiet)["resolve"]["root"]
        if package_id is None:
            raise FileError(
                f"manifest for Rust extention `{ext.name}` at path `{ext.path}` is a virtual manifest (a workspace root without a package).\n\n"
                "If you intended to build for a workspace member, set `path` for the extension to the member's Cargo.toml file."
            )

        cargo_args = self._cargo_args(ext=ext, release=not debug, quiet=quiet)

        rustc_args: List[str] = []
        rustflags: List[str] = []
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
            # If toolchain >= 1.64.0, use '--crate-type' option of cargo (instead of
            # rustc). See https://github.com/PyO3/setuptools-rust/issues/320
            if use_cargo_crate_type:
                rustc_args.extend(ext.rustc_flags)
            else:
                rustc_args += [
                    "--crate-type",
                    "cdylib",
                    *ext.rustc_flags,
                ]
            extra_rustc_args, extra_rustflags = self._config_specific_rust_args(ext)
            rustc_args += extra_rustc_args
            rustflags += extra_rustflags
            if use_cargo_crate_type and "--crate-type" not in cargo_args:
                cargo_args.extend(["--crate-type", "cdylib"])

            command = [
                self.cargo,
                "rustc",
                "--lib",
                "--message-format=json-render-diagnostics",
                "--manifest-path",
                ext.path,
                *cargo_args,
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

        if self.target is _Platform.CARGO_DEFAULT:
            targets: List[Optional[str]] = [None]
        elif self.target is _Platform.UNIVERSAL2:
            targets = list(_UNIVERSAL2_TARGETS)
        else:
            targets = [self.target]

        cargo_messages: Dict[str, List[str]] = {}
        for target in targets:
            target_command = command.copy()
            if target is None:
                # Normalize the entries in `cargo_messages` to always be in terms of the
                # actual target triple.
                target = get_rust_host(ext.env)
            else:
                target_command += ["--target", target]
            if rustc_args:
                target_command += ["--"]
                target_command += rustc_args

            if not quiet:
                print(" ".join(target_command), file=sys.stderr)

            # Execute cargo
            try:
                # If quiet, capture all output and only show it in the exception
                # If not quiet, forward all cargo output to stderr
                stderr = subprocess.PIPE if quiet else None
                cargo_messages[target] = check_subprocess_output(
                    target_command,
                    env=env,
                    stderr=stderr,
                    text=True,
                ).splitlines()
            except subprocess.CalledProcessError as e:
                # Don't include stdout in the formatted error as it is a huge dump
                # of cargo json lines which aren't helpful for the end user.
                raise CompileError(format_called_process_error(e, include_stdout=False))

            except OSError:
                raise ExecError(
                    "Unable to execute 'cargo' - this package "
                    "requires Rust to be installed and cargo to be on the PATH"
                )

        # Find the shared library that cargo hopefully produced and copy
        # it into the build directory as if it were produced by build_ext.

        dylib_paths = []

        if ext._uses_exec_binding():
            # Find artifact from cargo messages
            artifacts = _find_cargo_artifacts(
                [line for messages in cargo_messages.values() for line in messages],
                package_id=package_id,
                kinds={"bin"},
            )
            if self.target is _Platform.UNIVERSAL2:
                artifacts = _combine_universal2_artifacts(artifacts)
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
                    raise ExecError(
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
                [line for messages in cargo_messages.values() for line in messages],
                package_id=package_id,
                kinds={"cdylib", "dylib"},
            )
            if self.target is _Platform.UNIVERSAL2:
                artifacts = _combine_universal2_artifacts(artifacts)
            if len(artifacts) == 0:
                raise ExecError(
                    "Rust build failed; unable to find any cdylib or dylib build artifacts"
                )
            elif len(artifacts) > 1:
                raise ExecError(
                    f"Rust build failed; expected only one cdylib or dylib build artifact but found {artifacts}"
                )

            artifact_path = artifacts[0]

            if os.environ.get("CARGO") == "cross":
                artifact_path = _replace_cross_target_dir(
                    artifact_path, ext, quiet=quiet
                )

            # guaranteed to be just one element after checks above
            dylib_paths.append(_BuiltModule(ext.name, artifact_path))

        if not ext.data_files:
            return dylib_paths, []

        if self.target is _Platform.UNIVERSAL2:
            search_targets = ext.universal2_data_files_from.targets()
        else:
            search_targets = list(cargo_messages)
        out_dirs = [
            out_dir
            for target in search_targets
            if (out_dir := _find_cargo_out_dir(cargo_messages[target], package_id))
            is not None
        ]
        if not out_dirs:
            raise ExecError(
                f"extension {ext.name} requests data files, but no corresponding"
                " build-script out directories could be found"
            )

        return dylib_paths, out_dirs

    def install_extension(
        self,
        ext: RustExtension,
        dylib_paths: List["_BuiltModule"],
        build_artifact_dirs: List[Path],
    ) -> None:
        debug_build = self._is_debug_build(ext)

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
                exe = sysconfig.get_config_var("EXE")

                if isinstance(ext, RustBin):
                    # will install the rust binary into the scripts directory
                    bin_name = module_name
                    if exe is not None:
                        bin_name += exe

                    install_scripts = cast(
                        CommandInstallScripts,
                        self.get_finalized_command("install_scripts"),
                    )
                    ext_path = os.path.join(install_scripts.build_dir, bin_name)
                else:
                    # will install the rust binary into the module directory
                    ext_path = build_ext.get_ext_fullpath(module_name)

                    # add expected extension
                    ext_path, _, _ = _split_platform_and_extension(ext_path)
                    if exe is not None:
                        ext_path += exe

                    # if required, also generate a console script entry point
                    ext.install_script(module_name.split(".")[-1], ext_path)
            else:
                # will install the rust library into the module directory
                ext_path = self.get_dylib_ext_path(ext, module_name)

            os.makedirs(os.path.dirname(ext_path), exist_ok=True)

            # Make filenames relative to cwd where possible, to make logs and
            # errors below a little neater

            cwd = os.getcwd()
            if dylib_path.startswith(cwd):
                dylib_path = os.path.relpath(dylib_path, cwd)
            if ext_path.startswith(cwd):
                ext_path = os.path.relpath(ext_path, cwd)

            logger.info("Copying rust artifact from %s to %s", dylib_path, ext_path)

            # We want to atomically replace any existing library file. We can't
            # just copy the new library directly on top of the old one as that
            # causes the existing library to be modified (rather the replaced).
            # This means that any process that currently uses the shared library
            # will see it modified and likely segfault.
            #
            # We first copy the file to the same directory, as `os.replace`
            # doesn't work across file system boundaries.
            temp_ext_path = ext_path + "~"
            shutil.copyfile(dylib_path, temp_ext_path)
            try:
                os.replace(temp_ext_path, ext_path)
            except PermissionError as e:
                msg = f"{e}\n  hint: check permissions for {ext_path!r}"
                if sys.platform == "win32":
                    # On Windows, dll files are locked by the system when in use.
                    msg += "\n  hint: the file may be in use by another Python process"
                raise CompileError(msg)

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
                        check_subprocess_output(args, env=None)
                    except subprocess.CalledProcessError:
                        pass

            # executables, win32(cygwin)-dll's, and shared libraries on
            # Unix-like operating systems need X bits
            mode = os.stat(ext_path).st_mode
            mode |= (mode & 0o444) >> 2  # copy R bits to X
            os.chmod(ext_path, mode)

        if not ext.data_files:
            return

        # We'll delegate the finding of the package directories to Setuptools, so we
        # can be sure we're handling editable installs and other complex situations
        # correctly.
        build_py = cast(setuptools_build_py, self.get_finalized_command("build_py"))

        def get_package_dir(package: str) -> Path:
            if self.inplace:
                # If `inplace`, we have to ask `build_py` (like `build_ext` would).
                return Path(build_py.get_package_dir(package))
            # ... If not, `build_ext` knows where to put the package.
            return Path(build_ext.build_lib) / Path(*package.split("."))

        for source, package in ext.data_files.items():
            dest = get_package_dir(package)
            dest.mkdir(mode=0o755, parents=True, exist_ok=True)
            for artifact_dir in build_artifact_dirs:
                source_full = artifact_dir / source
                dest_full = dest / source_full.name
                if source_full.is_file():
                    logger.info(
                        "Copying data file from %s to %s", source_full, dest_full
                    )
                    shutil.copy2(source_full, dest_full)
                elif source_full.is_dir():
                    logger.info(
                        "Copying data directory from %s to %s", source_full, dest_full
                    )
                    shutil.copytree(source_full, dest_full, dirs_exist_ok=True)
                # This tacitly makes "no match" a silent non-error.

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
        bdist_wheel = _get_bdist_wheel_cmd(self.distribution, create=False)

        if bdist_wheel is None:
            # wheel package is not installed, not building a limited-api wheel
            return False
        else:
            return cast(_PyLimitedApi, bdist_wheel.py_limited_api)

    def _is_debug_build(self, ext: RustExtension) -> bool:
        if self.release:
            return False
        elif self.debug:
            return True
        elif ext.debug is not None:
            return ext.debug
        else:
            return bool(self.inplace)

    def _cargo_args(
        self,
        ext: RustExtension,
        release: bool,
        quiet: bool,
    ) -> List[str]:
        args = []
        ext_profile = ext.get_cargo_profile()
        env_profile = os.getenv("SETUPTOOLS_RUST_CARGO_PROFILE")
        if release and not ext_profile and not env_profile:
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

        if env_profile:
            if ext_profile:
                args = [p for p in args if not p.startswith("--profile=")]
                while True:
                    try:
                        index = args.index("--profile")
                        del args[index : index + 2]
                    except ValueError:
                        break

            args.extend(["--profile", env_profile])

        if ext.cargo_manifest_args is not None:
            args.extend(ext.cargo_manifest_args)

        return args

    def _config_specific_rust_args(
        self, ext: RustExtension
    ) -> Tuple[List[str], List[str]]:
        """Get extra arguments for `rustc` and the `RUSTFLAGS` environment variable
        that depend on the specific environmental configuration for the compilation
        target."""

        def apple_specific_rustc() -> List[str]:
            # Apple platforms require special linker arguments
            ext_basename = os.path.basename(self.get_dylib_ext_path(ext, ext.name))
            return [
                "-Clink-arg=-undefined",
                "-Clink-arg=dynamic_lookup",
                f"-Clink-arg=-Wl,-install_name,@rpath/{ext_basename}",
            ]

        rustc_args: List[str] = []  # Command-line arguments for rustc.
        rust_flags: List[str] = []  # Extras for the `RUSTFLAGS` environment variable.

        if self.target is _Platform.UNIVERSAL2:
            # In this case we're in a multi-target compilation, so there's no one single
            # `target_triple` to get configurations for.
            rustc_args += apple_specific_rustc()
            return rustc_args, rust_flags

        target_triple = None if self.target is _Platform.CARGO_DEFAULT else self.target
        rustc_cfgs = get_rustc_cfgs(target_triple, ext.env)
        target_os = rustc_cfgs.get("target_os")
        if target_os in ("macos", "ios", "tvos", "watchos"):
            rustc_args += apple_specific_rustc()
        if rustc_cfgs.get("target_env") == "musl":
            # Tell musl targets not to statically link libc. See
            # https://github.com/rust-lang/rust/issues/59302 for details.
            # This must go in the env otherwise rustc will refuse to build
            # the cdylib, see https://github.com/rust-lang/cargo/issues/10143
            rust_flags += ["-Ctarget-feature=-crt-static"]
        if (rustc_cfgs.get("target_arch"), target_os) == ("wasm32", "emscripten"):
            rustc_args += ["-C", "link-args=-sSIDE_MODULE=2 -sWASM_BIGINT"]
        return rustc_args, rust_flags


def _combine_universal2_artifacts(artifacts: List[str]) -> List[str]:
    """For a multi-target compilation corresponding to an intended universal2 build,
    combine each set of corresponding separate-target artifacts into a single universal2
    binary.

    Returns the constructed paths to the new combined artifacts."""
    to_combine = collections.defaultdict(list)
    for artifact in artifacts:
        target = next((t for t in _UNIVERSAL2_TARGETS if t in artifact), None)
        if target is None:
            raise ExecError(
                f"Rust build failed; compiled artifact '{artifact}' does not appear to"
                " be part of the expected universal2 build."
            )
        to_combine[artifact.replace(target + "/", "")].append(artifact)
    combined = []
    for output_path, input_paths in to_combine.items():
        if len(set(input_paths)) != len(_UNIVERSAL2_TARGETS):
            raise ExecError(
                f"Rust build failed; {input_paths} is not a complete set of artifacts"
                " for a universal2 build."
            )
        create_universal2_binary(output_path, input_paths)
        combined.append(output_path)
    return combined


def create_universal2_binary(output_path: str, input_paths: List[str]) -> None:
    # Try lipo first
    command = ["lipo", "-create", "-output", output_path, *input_paths]
    try:
        check_subprocess_output(command, env=None, text=True)
    except subprocess.CalledProcessError as e:
        output = e.output
        raise CompileError("lipo failed with code: %d\n%s" % (e.returncode, output))
    except OSError:
        # lipo not found, try using the fat-macho library
        try:
            from fat_macho import FatWriter
        except ImportError:
            raise ExecError(
                "failed to locate `lipo` or import `fat_macho.FatWriter`. "
                "Try installing with `pip install fat-macho` "
            )
        fat = FatWriter()
        for input_path in input_paths:
            with open(input_path, "rb") as f:
                fat.add(f.read())
        fat.write_to(output_path)


class _Platform(enum.Enum):
    """Special cases for the platform of the wheel we're targeting.

    The alternative to this enum is a string containing a literal target triple."""

    CARGO_DEFAULT = enum.auto()
    """The default target triple you get with `cargo build` without specifying `--target`."""
    UNIVERSAL2 = enum.auto()
    """The special 'universal2' wheel format, which is the arm64 and x86_64 macOS builds squashed
    together into one binary."""


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


def _prepare_build_environment(env: Env, ext: RustExtension) -> Dict[str, str]:
    """Prepares environment variables to use when executing cargo build."""

    base_executable = None
    if os.getenv("SETUPTOOLS_RUST_PEP517_USE_BASE_PYTHON"):
        base_executable = getattr(sys, "_base_executable")

    if base_executable and os.path.exists(base_executable):
        executable = os.path.realpath(base_executable)
    else:
        executable = sys.executable

    # Make sure that if pythonXX-sys is used, it builds against the current
    # executing python interpreter.
    bindir = os.path.dirname(executable)

    env_vars = (env.env or os.environ).copy()
    env_vars.update(
        {
            # disables rust's pkg-config seeking for specified packages,
            # which causes pythonXX-sys to fall back to detecting the
            # interpreter from the path.
            "PATH": os.path.join(bindir, env_vars.get("PATH", "")),
            "PYTHON_SYS_EXECUTABLE": env_vars.get("PYTHON_SYS_EXECUTABLE", executable),
            "PYO3_PYTHON": env_vars.get("PYO3_PYTHON", executable),
        }
    )

    if ext.binding == Binding.PyO3:
        env_vars.setdefault("PYO3_BUILD_EXTENSION_MODULE", "1")

    return env_vars


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
                features.add("pyo3/abi3")
        return features
    elif ext.binding is Binding.RustCPython:
        return {"cpython/python3-sys", "cpython/extension-module"}
    else:
        raise PlatformError(f"unknown Rust binding: '{ext.binding}'")


_PyLimitedApi = Literal["cp37", "cp38", "cp39", "cp310", "cp311", "cp312", True, False]


def _override_cargo_default_target(plat_name: str, env: Env) -> Union[str, _Platform]:
    """Get a platform-specific override, if one is needed for correctness."""
    override: Union[str, _Platform] = _Platform.CARGO_DEFAULT
    if plat_name in ("win32", "win-amd64"):
        toolchain = (
            "gnu" if get_rustc_cfgs(None, env).get("target_env") == "gnu" else "msvc"
        )
        # If we've got a 32-bit Python, we need to make sure Rust will build for a 32-bit target,
        # even though the host system may well be 64-bit.
        arch = "i686" if plat_name == "win32" else "x86_64"
        override = f"{arch}-pc-windows-{toolchain}"
    elif plat_name.startswith("macosx-"):
        override = _macos_target_from_arch_flags(os.environ.get("ARCHFLAGS"))
        if override is _Platform.CARGO_DEFAULT and platform.machine() == "x86_64":
            override = "x86_64-apple-darwin"

    if isinstance(override, str) and override == get_rust_host(env):
        # If the override we asserted resolves to the same that `rustc` would do by default, we swap
        # back to specifying the `CARGO_DEFAULT` to avoid creating spurious specific-target
        # directories in the temporary build directory.
        override = _Platform.CARGO_DEFAULT
    return override


def _macos_target_from_arch_flags(arch_flags: Optional[str]) -> Union[str, _Platform]:
    """Detect the macOS target to compile for, based on what (if anything) is set in the
    `ARCHFLAGS`."""
    if arch_flags is None:
        return _Platform.CARGO_DEFAULT
    intel = "x86_64" in arch_flags
    arm = "arm64" in arch_flags
    if intel and arm:
        return _Platform.UNIVERSAL2
    if intel:
        return "x86_64-apple-darwin"
    if arm:
        return "aarch64-apple-darwin"
    return _Platform.CARGO_DEFAULT


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
    >>> _find_cargo_artifacts(
    ...    [
    ...        '{"some_irrelevant_message": []}',
    ...        '{"reason": "compiler-artifact", "package_id": "some_id", "target": {"kind": ["bin"]}, "filenames":[], "executable": "/target/debug/some_exe"}'
    ...    ],
    ...    package_id="some_id",
    ...    kinds={"bin"},
    ... )
    ['/target/debug/some_exe']
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
                filenames = parsed["filenames"]
                if not filenames and parsed.get("executable"):
                    # Use parsed["executable"] as the filename when filenames are empty
                    # See https://github.com/PyO3/maturin/issues/2370
                    filenames = [parsed["executable"]]
                for artifact_kind, filename in zip(parsed["target"]["kind"], filenames):
                    if artifact_kind in kinds:
                        artifacts.append(filename)
    return artifacts


def _find_cargo_out_dir(cargo_messages: List[str], package_id: str) -> Optional[Path]:
    # Chances are that the line we're looking for will be the third laste line in the
    # messages.  The last is the completion report, the penultimate is generally the
    # build of the final artifact.
    for messsage in reversed(cargo_messages):
        if "build-script-executed" not in messsage or package_id not in messsage:
            continue
        parsed = json.loads(messsage)
        if parsed.get("package_id") == package_id:
            out_dir = parsed.get("out_dir")
            return None if out_dir is None else Path(out_dir)
    return None


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


def _get_bdist_wheel_cmd(
    dist: Distribution, create: Literal[True, False] = True
) -> Optional[CommandBdistWheel]:
    try:
        cmd_obj = dist.get_command_obj("bdist_wheel", create=create)
        cmd_obj.ensure_finalized()  # type: ignore[union-attr]
        return cast(CommandBdistWheel, cmd_obj)
    except Exception:
        return None
