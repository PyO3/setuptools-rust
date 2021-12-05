import glob
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
from distutils import log
from distutils.command.build import build as CommandBuild
from distutils.errors import (
    CompileError,
    DistutilsExecError,
    DistutilsFileError,
    DistutilsPlatformError,
)
from distutils.sysconfig import get_config_var
from subprocess import check_output
from typing import Dict, List, NamedTuple, Optional, Union, cast

from setuptools.command.build_ext import build_ext as CommandBuildExt
from setuptools.command.build_ext import get_abi3_suffix
from typing_extensions import Literal

from .command import RustCommand
from .extension import Binding, RustExtension, Strip
from .utils import (
    PyLimitedApi,
    binding_features,
    get_rust_target_info,
    get_rust_target_list,
    split_platform_and_extension,
)


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

    plat_name: Optional[str]

    def initialize_options(self) -> None:
        super().initialize_options()
        self.inplace = None
        self.debug = None
        self.release = None
        self.qbuild = None
        self.build_temp = None
        self.plat_name = None
        self.target = os.getenv("CARGO_BUILD_TARGET")
        self.cargo = os.getenv("CARGO", "cargo")

    def finalize_options(self) -> None:
        super().finalize_options()

        if self.plat_name is None:
            self.plat_name = cast(
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

    def run_for_extension(self, ext: RustExtension) -> None:
        assert self.plat_name is not None

        arch_flags = os.getenv("ARCHFLAGS")
        universal2 = False
        if self.plat_name.startswith("macosx-") and arch_flags:
            universal2 = "x86_64" in arch_flags and "arm64" in arch_flags
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
        self, ext: RustExtension, forced_target_triple: Optional[str]
    ) -> List["_BuiltModule"]:

        target_info = self._detect_rust_target(forced_target_triple)
        if target_info is not None:
            target_triple = target_info.triple
            cross_lib = target_info.cross_lib
            linker = target_info.linker
            # We're ignoring target_info.linker_args for now because we're not
            # sure if they will always do the right thing. Might help with some
            # of the OS-specific logic if it does.

        else:
            target_triple = None
            cross_lib = None
            linker = None

        rustc_cfgs = _get_rustc_cfgs(target_triple)

        env = _prepare_build_environment(cross_lib)

        if not os.path.exists(ext.path):
            raise DistutilsFileError(
                f"can't find Rust extension project file: {ext.path}"
            )

        # Find where to put the temporary build files created by `cargo`
        target_dir = _base_cargo_target_dir(ext)
        if target_triple is not None:
            target_dir = os.path.join(target_dir, target_triple)

        quiet = self.qbuild or ext.quiet
        debug = self._is_debug_build(ext)
        cargo_args = self._cargo_args(
            ext=ext, target_triple=target_triple, release=not debug, quiet=quiet
        )

        if ext._uses_exec_binding():
            command = [self.cargo, "build", "--manifest-path", ext.path, *cargo_args]

        else:
            rustc_args = [
                "--crate-type",
                "cdylib",
            ]

            if ext.rustc_flags is not None:
                rustc_args.extend(ext.rustc_flags)

            if linker is not None:
                rustc_args.extend(["-C", "linker=" + linker])

            # OSX requires special linker arguments
            if sys.platform == "darwin":
                ext_basename = os.path.basename(self.get_dylib_ext_path(ext, ext.name))
                rustc_args.extend(
                    [
                        "-C",
                        f"link-args=-undefined dynamic_lookup -Wl,-install_name,@rpath/{ext_basename}",
                    ]
                )

            if ext.native:
                rustc_args.extend(["-C", "target-cpu=native"])

            # Tell musl targets not to statically link libc. See
            # https://github.com/rust-lang/rust/issues/59302 for details.
            if rustc_cfgs.get("target_env") == "musl":
                # This must go in the env otherwise rustc will refuse to build
                # the cdylib, see https://github.com/rust-lang/cargo/issues/10143
                MUSL_FLAGS = "-C target-feature=-crt-static"
                rustflags = env.get("RUSTFLAGS")
                if rustflags is not None:
                    env["RUSTFLAGS"] = f"{rustflags} {MUSL_FLAGS}"
                else:
                    env["RUSTFLAGS"] = MUSL_FLAGS

                # Include this in the command-line anyway, so that when verbose
                # logging enabled the user will see that this flag is in use.
                rustc_args.extend(MUSL_FLAGS.split())

            command = [
                self.cargo,
                "rustc",
                "--lib",
                "--manifest-path",
                ext.path,
                *cargo_args,
                "--",
                *rustc_args,
            ]

        if not quiet:
            print(" ".join(command), file=sys.stderr)

        # Execute cargo
        try:
            output = subprocess.check_output(command, env=env, encoding="latin-1")
        except subprocess.CalledProcessError as e:
            raise CompileError(f"cargo failed with code: {e.returncode}\n{e.output}")

        except OSError:
            raise DistutilsExecError(
                "Unable to execute 'cargo' - this package "
                "requires Rust to be installed and cargo to be on the PATH"
            )

        if not quiet:
            if output:
                print(output, file=sys.stderr)

        # Find the shared library that cargo hopefully produced and copy
        # it into the build directory as if it were produced by build_ext.

        artifacts_dir = os.path.join(target_dir, "debug" if debug else "release")
        dylib_paths = []

        if ext._uses_exec_binding():
            for name, dest in ext.target.items():
                if not name:
                    name = dest.split(".")[-1]
                exe = sysconfig.get_config_var("EXE")
                if exe is not None:
                    name += exe

                path = os.path.join(artifacts_dir, name)
                if os.access(path, os.X_OK):
                    dylib_paths.append(_BuiltModule(dest, path))
                else:
                    raise DistutilsExecError(
                        "Rust build failed; "
                        f"unable to find executable '{name}' in '{artifacts_dir}'"
                    )
        else:
            if sys.platform == "win32" or sys.platform == "cygwin":
                dylib_ext = "dll"
            elif sys.platform == "darwin":
                dylib_ext = "dylib"
            else:
                dylib_ext = "so"

            wildcard_so = "*{}.{}".format(ext.get_lib_name(), dylib_ext)

            try:
                dylib_paths.append(
                    _BuiltModule(
                        ext.name,
                        next(glob.iglob(os.path.join(artifacts_dir, wildcard_so))),
                    )
                )
            except StopIteration:
                raise DistutilsExecError(
                    f"Rust build failed; unable to find any {wildcard_so} in {artifacts_dir}"
                )
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
                ext_path, _, _ = split_platform_and_extension(ext_path)

                # Add expected extension
                exe = sysconfig.get_config_var("EXE")
                if exe is not None:
                    ext_path += exe

                os.makedirs(os.path.dirname(ext_path), exist_ok=True)
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
            ext_path, _, extension = split_platform_and_extension(ext_path)
            # rust.so, removed platform tag
            ext_path += extension
        return ext_path

    def _py_limited_api(self) -> PyLimitedApi:
        bdist_wheel = self.distribution.get_command_obj("bdist_wheel", create=False)

        if bdist_wheel is None:
            # wheel package is not installed, not building a limited-api wheel
            return False
        else:
            from wheel.bdist_wheel import bdist_wheel as CommandBdistWheel

            bdist_wheel_command = cast(CommandBdistWheel, bdist_wheel)  # type: ignore[no-any-unimported]
            bdist_wheel_command.ensure_finalized()
            return cast(PyLimitedApi, bdist_wheel_command.py_limited_api)

    def _detect_rust_target(
        self, forced_target_triple: Optional[str]
    ) -> Optional["_TargetInfo"]:
        cross_compile_info = _detect_unix_cross_compile_info()
        if cross_compile_info is not None:
            cross_target_info = cross_compile_info.to_target_info()
            if forced_target_triple is not None:
                if (
                    cross_target_info is not None
                    and not cross_target_info.is_compatible_with(forced_target_triple)
                ):
                    self.warn(
                        f"Forced Rust target `{forced_target_triple}` is not "
                        f"compatible with deduced Rust target "
                        f"`{cross_target_info.triple}` - the built package "
                        f" may not import successfully once installed."
                    )

                # Forcing the target in a cross-compile environment; use
                # the cross-compile information in combination with the
                # forced target
                return _TargetInfo(
                    forced_target_triple,
                    cross_compile_info.cross_lib,
                    cross_compile_info.linker,
                    cross_compile_info.linker_args,
                )
            elif cross_target_info is not None:
                return cross_target_info
            else:
                raise DistutilsPlatformError(
                    "Don't know the correct rust target for system type "
                    f"{cross_compile_info.host_type}. Please set the "
                    "CARGO_BUILD_TARGET environment variable."
                )

        elif forced_target_triple is not None:
            return _TargetInfo.for_triple(forced_target_triple)

        else:
            # Automatic target detection can be overridden via the CARGO_BUILD_TARGET
            # environment variable or --target command line option
            return self._detect_local_rust_target()

    def _detect_local_rust_target(self) -> Optional["_TargetInfo"]:
        """Attempts to infer the correct Rust target from build environment for
        some edge cases."""
        assert self.plat_name is not None

        # If we are on a 64-bit machine, but running a 32-bit Python, then
        # we'll target a 32-bit Rust build.
        if self.plat_name == "win32":
            if _get_rustc_cfgs(None).get("target_env") == "gnu":
                return _TargetInfo.for_triple("i686-pc-windows-gnu")
            return _TargetInfo.for_triple("i686-pc-windows-msvc")
        elif self.plat_name == "win-amd64":
            if _get_rustc_cfgs(None).get("target_env") == "gnu":
                return _TargetInfo.for_triple("x86_64-pc-windows-gnu")
            return _TargetInfo.for_triple("x86_64-pc-windows-msvc")
        elif self.plat_name.startswith("macosx-") and platform.machine() == "x86_64":
            # x86_64 or arm64 macOS targeting x86_64
            return _TargetInfo.for_triple("x86_64-apple-darwin")
        else:
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
            args.append("--release")

        if quiet:
            args.append("-q")

        elif self.verbose:
            # cargo only have -vv
            verbose_level = "v" * min(self.verbose, 2)
            args.append(f"-{verbose_level}")

        features = {
            *ext.features,
            *binding_features(ext, py_limited_api=self._py_limited_api()),
        }

        if features:
            args.extend(["--features", " ".join(features)])

        if ext.args is not None:
            args.extend(ext.args)

        return args


def create_universal2_binary(output_path: str, input_paths: List[str]) -> None:
    # Try lipo first
    command = ["lipo", "-create", "-output", output_path, *input_paths]
    try:
        subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        output = e.output
        if isinstance(output, bytes):
            output = e.output.decode("latin-1").strip()
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


class _TargetInfo(NamedTuple):
    triple: str
    cross_lib: Optional[str]
    linker: Optional[str]
    linker_args: Optional[str]

    @staticmethod
    def for_triple(triple: str) -> "_TargetInfo":
        return _TargetInfo(triple, None, None, None)

    def is_compatible_with(self, target: str) -> bool:
        if self.triple == target:
            return True

        # the vendor field can be ignored, so x86_64-pc-linux-gnu is compatible
        # with x86_64-unknown-linux-gnu
        if _replace_vendor_with_unknown(self.triple) == target:
            return True

        return False


class _CrossCompileInfo(NamedTuple):
    host_type: str
    cross_lib: Optional[str]
    linker: Optional[str]
    linker_args: Optional[str]

    def to_target_info(self) -> Optional[_TargetInfo]:
        """Maps this cross compile info to target info.

        Returns None if the corresponding target information could not be
        deduced.
        """
        # hopefully an exact match
        targets = get_rust_target_list()
        if self.host_type in targets:
            return _TargetInfo(
                self.host_type, self.cross_lib, self.linker, self.linker_args
            )

        # the vendor field can be ignored, so x86_64-pc-linux-gnu is compatible
        # with x86_64-unknown-linux-gnu
        without_vendor = _replace_vendor_with_unknown(self.host_type)
        if without_vendor is not None and without_vendor in targets:
            return _TargetInfo(
                without_vendor, self.cross_lib, self.linker, self.linker_args
            )

        return None


def _detect_unix_cross_compile_info() -> Optional["_CrossCompileInfo"]:
    # See https://github.com/PyO3/setuptools-rust/issues/138
    # This is to support cross compiling on *NIX, where plat_name isn't
    # necessarily the same as the system we are running on.  *NIX systems
    # have more detailed information available in sysconfig. We need that
    # because plat_name doesn't give us information on e.g., glibc vs musl.
    host_type = sysconfig.get_config_var("HOST_GNU_TYPE")
    build_type = sysconfig.get_config_var("BUILD_GNU_TYPE")

    if not host_type or host_type == build_type:
        # not *NIX, or not cross compiling
        return None

    if "apple-darwin" in host_type and (build_type and "apple-darwin" in build_type):
        # On macos and the build and host differ. This is probably an arm
        # Python which was built on x86_64. Don't try to handle this for now.
        # (See https://github.com/PyO3/setuptools-rust/issues/192)
        return None

    stdlib = sysconfig.get_path("stdlib")
    assert stdlib is not None
    cross_lib = os.path.dirname(stdlib)

    bldshared = sysconfig.get_config_var("BLDSHARED")
    if not bldshared:
        linker = None
        linker_args = None
    else:
        [linker, linker_args] = bldshared.split(maxsplit=1)

    return _CrossCompileInfo(host_type, cross_lib, linker, linker_args)


_RustcCfgs = Dict[str, Optional[str]]


def _get_rustc_cfgs(target_triple: Optional[str]) -> _RustcCfgs:
    cfgs: _RustcCfgs = {}
    for entry in get_rust_target_info(target_triple):
        maybe_split = entry.split("=", maxsplit=1)
        if len(maybe_split) == 2:
            cfgs[maybe_split[0]] = maybe_split[1].strip('"')
        else:
            assert len(maybe_split) == 1
            cfgs[maybe_split[0]] = None
    return cfgs


def _replace_vendor_with_unknown(target: str) -> Optional[str]:
    """Replaces vendor in the target triple with unknown.

    Returns None if the target is not made of 4 parts.
    """
    components = target.split("-")
    if len(components) != 4:
        return None
    components[1] = "unknown"
    return "-".join(components)


def _prepare_build_environment(cross_lib: Optional[str]) -> Dict[str, str]:
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

    if cross_lib:
        env.setdefault("PYO3_CROSS_LIB_DIR", cross_lib)

    return env


def _base_cargo_target_dir(ext: RustExtension) -> str:
    """Returns the root target directory cargo will use.

    If --target is passed to cargo in the command line, the target directory
    will have the target appended as a child.
    """
    target_directory = ext._metadata()["target_directory"]
    assert isinstance(
        target_directory, str
    ), "expected cargo metadata to contain a string target directory"
    return target_directory


def _is_py_limited_api(
    ext_setting: Literal["auto", True, False],
    wheel_setting: Optional[PyLimitedApi],
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
