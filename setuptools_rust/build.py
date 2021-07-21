import glob
import json
import os
import platform
import shutil
import sys
import subprocess
import sysconfig
from distutils.errors import (
    CompileError,
    DistutilsExecError,
    DistutilsFileError,
    DistutilsPlatformError,
)
from distutils.sysconfig import get_config_var
from setuptools.command.build_ext import get_abi3_suffix
from subprocess import check_output

from .command import RustCommand
from .extension import Binding, RustExtension, Strip
from .utils import binding_features, get_rust_target_info, get_rust_target_list

class _TargetInfo:
    def __init__(self, triple=None, cross_lib=None, linker=None, link_args=None):
        self.triple = triple
        self.cross_lib = cross_lib
        self.linker = linker
        self.link_args = link_args

class build_rust(RustCommand):
    """ Command for building Rust crates via cargo. """

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
        ("target", None, "Build for the target triple"),
    ]
    boolean_options = ["inplace", "debug", "release", "qbuild"]

    def initialize_options(self):
        super().initialize_options()
        self.inplace = None
        self.debug = None
        self.release = None
        self.qbuild = None
        self.build_temp = None
        self.plat_name = None
        self.target = os.getenv("CARGO_BUILD_TARGET")

    def finalize_options(self):
        super().finalize_options()

        if self.plat_name is None:
            self.plat_name = self.get_finalized_command('build').plat_name

        # Inherit settings from the `build_ext` command
        self.set_undefined_options(
            "build_ext",
            ("build_temp", "build_temp"),
            ("debug", "debug"),
            ("inplace", "inplace"),
        )

    def get_target_info(self):
        # If we are on a 64-bit machine, but running a 32-bit Python, then
        # we'll target a 32-bit Rust build.
        # Automatic target detection can be overridden via the CARGO_BUILD_TARGET
        # environment variable or --target command line option
        if self.target:
            return _TargetInfo(self.target)
        elif self.plat_name == "win32":
            return _TargetInfo("i686-pc-windows-msvc")
        elif self.plat_name == "win-amd64":
            return _TargetInfo("x86_64-pc-windows-msvc")
        elif self.plat_name.startswith("macosx-") and platform.machine() == "x86_64":
            # x86_64 or arm64 macOS targeting x86_64
            return _TargetInfo("x86_64-apple-darwin")
        else:
            return self.get_nix_target_info()

    def get_nix_target_info(self):
        # See https://github.com/PyO3/setuptools-rust/issues/138
        # This is to support cross compiling on *NIX, where plat_name isn't
        # necessarily the same as the system we are running on.  *NIX systems
        # have more detailed information available in sysconfig. We need that
        # because plat_name doesn't give us information on e.g., glibc vs musl.
        host_type = sysconfig.get_config_var('HOST_GNU_TYPE')
        build_type = sysconfig.get_config_var('BUILD_GNU_TYPE')

        if not host_type or host_type == build_type:
            # not *NIX, or not cross compiling
            return _TargetInfo()

        stdlib = sysconfig.get_path('stdlib')
        cross_lib = os.path.dirname(stdlib)

        bldshared = sysconfig.get_config_var('BLDSHARED')
        if not bldshared:
            linker = None
            linker_args = None
        else:
            bldshared = bldshared.split()
            linker = bldshared[0]
            linker_args = bldshared[1:]

        # hopefully an exact match
        targets = get_rust_target_list()
        if host_type in targets:
            return _TargetInfo(host_type, cross_lib, linker, linker_args)

        # the vendor field can be ignored, so x86_64-pc-linux-gnu is compatible
        # with x86_64-unknown-linux-gnu
        components = host_type.split('-')
        if len(components) == 4:
            components[1] = 'unknown'
            host_type2 = '-'.join(components)
            if host_type2 in targets:
                return _TargetInfo(host_type2, cross_lib, linker, linker_args)

        raise DistutilsPlatformError(
                "Don't know the correct rust target for system type %s. Please "
                "set the CARGO_BUILD_TARGET environment variable." % host_type)

    def run_for_extension(self, ext: RustExtension):
        arch_flags = os.getenv("ARCHFLAGS")
        universal2 = False
        if self.plat_name.startswith("macosx-") and arch_flags:
            universal2 = "x86_64" in arch_flags and "arm64" in arch_flags
        if universal2:
            arm64_dylib_paths = self.build_extension(ext, "aarch64-apple-darwin")
            x86_64_dylib_paths = self.build_extension(ext, "x86_64-apple-darwin")
            dylib_paths = []
            for (target_fname, arm64_dylib), (_, x86_64_dylib) in zip(arm64_dylib_paths, x86_64_dylib_paths):
                fat_dylib_path = arm64_dylib.replace("aarch64-apple-darwin/", "")
                self.create_universal2_binary(fat_dylib_path, [arm64_dylib, x86_64_dylib])
                dylib_paths.append((target_fname, fat_dylib_path))
        else:
            dylib_paths = self.build_extension(ext)
        self.install_extension(ext, dylib_paths)

    def build_extension(self, ext: RustExtension, target_triple=None):
        executable = ext.binding == Binding.Exec

        if target_triple is None:
            target_info = self.get_target_info()
        else:
            target_info = _TargetInfo(target_triple)
        rust_target_info = get_rust_target_info(target_info.triple)

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
                "PYTHON_SYS_EXECUTABLE": os.environ.get("PYTHON_SYS_EXECUTABLE", sys.executable),
                "PYO3_PYTHON": os.environ.get("PYO3_PYTHON", sys.executable),
            }
        )

        if target_info.cross_lib:
            env.setdefault("PYO3_CROSS_LIB_DIR", target_info.cross_lib)

        rustflags = ""

        target_args = []
        if target_info.triple is not None:
            target_args = ["--target", target_info.triple]

        # Find where to put the temporary build files created by `cargo`
        metadata_command = [
            "cargo",
            "metadata",
            "--manifest-path",
            ext.path,
            "--format-version",
            "1",
        ]
        metadata = json.loads(check_output(metadata_command))
        target_dir = metadata["target_directory"]

        if not os.path.exists(ext.path):
            raise DistutilsFileError(
                f"can't find Rust extension project file: {ext.path}"
            )

        bdist_wheel = self.get_finalized_command('bdist_wheel')
        features = {
            *ext.features,
            *binding_features(ext, py_limited_api=bdist_wheel.py_limited_api)
        }

        debug_build = ext.debug if ext.debug is not None else self.inplace
        debug_build = self.debug if self.debug is not None else debug_build
        if self.release:
            debug_build = False

        quiet = self.qbuild or ext.quiet

        # build cargo command
        feature_args = ["--features", " ".join(features)] if features else []

        if executable:
            args = (
                ["cargo", "build", "--manifest-path", ext.path]
                + feature_args
                + target_args
                + list(ext.args or [])
            )
            if not debug_build:
                args.append("--release")
            if quiet:
                args.append("-q")
            elif self.verbose:
                # cargo only have -vv
                verbose_level = 'v' * min(self.verbose, 2)
                args.append(f"-{verbose_level}")

        else:
            args = (
                ["cargo", "rustc", "--lib", "--manifest-path", ext.path]
                + feature_args
                + target_args
                + list(ext.args or [])
            )
            if not debug_build:
                args.append("--release")
            if quiet:
                args.append("-q")
            elif self.verbose:
                # cargo only have -vv
                verbose_level = 'v' * min(self.verbose, 2)
                args.append(f"-{verbose_level}")

            args.extend(["--", "--crate-type", "cdylib"])
            args.extend(ext.rustc_flags or [])

            if target_info.linker is not None:
                args.extend(["-C", "linker=" + target_info.linker])
            # We're ignoring target_info.link_args for now because we're not
            # sure if they will always do the right thing. Might help with some
            # of the OS-specific logic below if it does.

            # OSX requires special linker argument
            if sys.platform == "darwin":
                args.extend(
                    ["-C", "link-arg=-undefined", "-C", "link-arg=dynamic_lookup"]
                )
            # Tell musl targets not to statically link libc. See
            # https://github.com/rust-lang/rust/issues/59302 for details.
            if b'target_env="musl"' in rust_target_info:
                rustflags += " -C target-feature=-crt-static"

        if not quiet:
            print(" ".join(args), file=sys.stderr)

        if ext.native:
            rustflags += " -C target-cpu=native"

        if not executable and sys.platform == "darwin":
            ext_basename = os.path.basename(self.get_dylib_ext_path(ext, ext.name))
            rustflags += f" -C link-args=-Wl,-install_name,@rpath/{ext_basename}"

        if rustflags:
            env["RUSTFLAGS"] = (env.get("RUSTFLAGS", "") + " " + rustflags).strip()

        # Execute cargo
        try:
            output = subprocess.check_output(args, env=env, encoding="latin-1")
        except subprocess.CalledProcessError as e:
            raise CompileError(
                f"cargo failed with code: {e.returncode}\n{e.output}"
            )

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
        if debug_build:
            suffix = "debug"
        else:
            suffix = "release"

        # location of cargo compiled files
        artifactsdir = os.path.join(target_dir, target_info.triple or "", suffix)
        dylib_paths = []

        if executable:
            for name, dest in ext.target.items():
                if name:
                    path = os.path.join(artifactsdir, name)
                    if os.access(path, os.X_OK):
                        dylib_paths.append((dest, path))
                        continue
                    else:
                        raise DistutilsExecError(
                            "Rust build failed; "
                            f"unable to find executable '{name}' in '{target_dir}'"
                        )
                else:
                    # search executable
                    for name in os.listdir(artifactsdir):
                        path = os.path.join(artifactsdir, name)
                        if name.startswith(".") or not os.path.isfile(path):
                            continue

                        if os.access(path, os.X_OK):
                            dylib_paths.append((ext.name, path))
                            break

            if not dylib_paths:
                raise DistutilsExecError(
                    f"Rust build failed; unable to find executable in {target_dir}"
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
                    (
                        ext.name,
                        next(glob.iglob(os.path.join(artifactsdir, wildcard_so))),
                    )
                )
            except StopIteration:
                raise DistutilsExecError(
                    f"Rust build failed; unable to find any {wildcard_so} in {artifactsdir}"
                )
        return dylib_paths

    def install_extension(self, ext: RustExtension, dylib_paths):
        executable = ext.binding == Binding.Exec
        debug_build = ext.debug if ext.debug is not None else self.inplace
        debug_build = self.debug if self.debug is not None else debug_build
        if self.release:
            debug_build = False
        # Ask build_ext where the shared library would go if it had built it,
        # then copy it there.
        build_ext = self.get_finalized_command("build_ext")
        build_ext.inplace = self.inplace

        for target_fname, dylib_path in dylib_paths:
            if not target_fname:
                target_fname = os.path.basename(
                    os.path.splitext(os.path.basename(dylib_path)[3:])[0]
                )

            if executable:
                ext_path = build_ext.get_ext_fullpath(target_fname)
                # remove .so extension
                ext_path, _ = os.path.splitext(ext_path)
                # remove python3 extension (i.e. cpython-36m)
                ext_path, _ = os.path.splitext(ext_path)

                os.makedirs(os.path.dirname(ext_path), exist_ok=True)
                ext.install_script(ext_path)
            else:
                ext_path = self.get_dylib_ext_path(ext, target_fname)
                os.makedirs(os.path.dirname(ext_path), exist_ok=True)

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

    def get_dylib_ext_path(
        self,
        ext: RustExtension,
        target_fname: str
    ) -> str:
        build_ext = self.get_finalized_command("build_ext")
        bdist_wheel = self.get_finalized_command("bdist_wheel")

        filename = build_ext.get_ext_fullpath(target_fname)

        if (
            (ext.py_limited_api == "auto" and bdist_wheel.py_limited_api)
            or (ext.py_limited_api)
        ):
            abi3_suffix = get_abi3_suffix()
            if abi3_suffix is not None:
                so_ext = get_config_var('EXT_SUFFIX')
                filename = filename[:-len(so_ext)] + get_abi3_suffix()

        return filename

    @staticmethod
    def create_universal2_binary(output_path, input_paths):
        # Try lipo first
        command = ["lipo", "-create", "-output", output_path, *input_paths]
        try:
            subprocess.check_output(command)
        except subprocess.CalledProcessError as e:
            output = e.output
            if isinstance(output, bytes):
                output = e.output.decode("latin-1").strip()
            raise CompileError(
                "lipo failed with code: %d\n%s" % (e.returncode, output)
            )
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
