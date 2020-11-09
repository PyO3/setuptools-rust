from __future__ import print_function, absolute_import
import glob
import json
import os
import shutil
import sys
import subprocess
from distutils.cmd import Command
from distutils.errors import (
    CompileError,
    DistutilsExecError,
    DistutilsFileError,
    DistutilsPlatformError,
    DistutilsSetupError,
)
from subprocess import check_output

from .extension import RustExtension
from .utils import (
    Binding, Strip, cpython_feature, get_rust_version, get_rust_target_info
)


class build_rust(Command):
    """ Command for building rust crates via cargo. """

    description = "build Rust extensions (compile/link to build directory)"

    user_options = [
        (
            "inplace",
            "i",
            "ignore build-lib and put compiled extensions into the source "
            + "directory alongside your pure Python modules",
        ),
        ("debug", "d", "Force debug to true for all rust extensions "),
        ("release", "r", "Force debug to false for all rust extensions "),
        ("qbuild", None, "Force enable quiet option for all rust extensions "),
        (
            "build-temp",
            "t",
            "directory for temporary files (cargo 'target' directory) ",
        ),
    ]
    boolean_options = ["inplace", "debug", "release", "qbuild"]

    def initialize_options(self):
        self.extensions = ()
        self.inplace = None
        self.debug = None
        self.release = None
        self.qbuild = None
        self.build_temp = None
        self.plat_name = None

    def finalize_options(self):
        self.extensions = [
            ext
            for ext in self.distribution.rust_extensions
            if isinstance(ext, RustExtension)
        ]

        # Inherit settings from the `build_ext` command
        self.set_undefined_options(
            "build_ext",
            ("build_temp", "build_temp"),
            ("debug", "debug"),
            ("inplace", "inplace"),
        )

    def build_extension(self, ext):
        executable = ext.binding == Binding.Exec

        rust_target_info = get_rust_target_info()

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
                "PYTHON_SYS_EXECUTABLE": sys.executable,
                "PYO3_PYTHON": sys.executable,
            }
        )
        rustflags = ""

        # If we are on a 64-bit machine, but running a 32-bit Python, then
        # we'll target a 32-bit Rust build.
        # TODO: include --target for all platforms so env vars can't break the build
        target_triple = None
        target_args = []
        if self.plat_name == "win32":
            target_triple = "i686-pc-windows-msvc"
        elif self.plat_name == "win-amd64":
            target_triple = "x86_64-pc-windows-msvc"

        if target_triple is not None:
            target_args = ["--target", target_triple]

        # Find where to put the temporary build files created by `cargo`
        metadata_command = [
            "cargo",
            "metadata",
            "--manifest-path",
            ext.path,
            "--format-version",
            "1",
        ]
        # The decoding is needed for python 3.5 compatibility
        metadata = json.loads(check_output(metadata_command).decode("utf-8"))
        target_dir = metadata["target_directory"]

        if not os.path.exists(ext.path):
            raise DistutilsFileError(
                "Can not find rust extension project file: %s" % ext.path
            )

        features = set(ext.features)
        features.update(cpython_feature(binding=ext.binding))

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
                args.append("--verbose")

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
                args.append("--verbose")

            args.extend(["--", "--crate-type", "cdylib"])
            args.extend(ext.rustc_flags or [])

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

        if rustflags:
            env["RUSTFLAGS"] = rustflags

        # Execute cargo
        try:
            output = subprocess.check_output(args, env=env)
        except subprocess.CalledProcessError as e:
            output = e.output
            if isinstance(output, bytes):
                output = e.output.decode("latin-1").strip()
            raise CompileError(
                "cargo failed with code: %d\n%s" % (e.returncode, output)
            )

        except OSError:
            raise DistutilsExecError(
                "Unable to execute 'cargo' - this package "
                "requires rust to be installed and cargo to be on the PATH"
            )

        if not quiet:
            if isinstance(output, bytes):
                output = output.decode("latin-1")
            if output:
                print(output, file=sys.stderr)

        # Find the shared library that cargo hopefully produced and copy
        # it into the build directory as if it were produced by build_ext.
        if debug_build:
            suffix = "debug"
        else:
            suffix = "release"

        # location of cargo compiled files
        artifactsdir = os.path.join(target_dir, target_triple or "", suffix)
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
                            "rust build failed; "
                            'unable to find executable "%s" in %s' % (name, target_dir)
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
                    "rust build failed; unable to find executable in %s" % target_dir
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
                    "rust build failed; unable to find any %s in %s"
                    % (wildcard_so, artifactsdir)
                )

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

                ext.install_script(ext_path)
            else:
                # Technically it's supposed to contain a
                # `setuptools.Extension`, but in practice the only attribute it
                # checks is `ext.py_limited_api`.
                modpath = target_fname.split('.')[-1]
                assert modpath not in build_ext.ext_map
                build_ext.ext_map[modpath] = ext
                try:
                    ext_path = build_ext.get_ext_fullpath(target_fname)
                finally:
                    del build_ext.ext_map[modpath]

            try:
                os.makedirs(os.path.dirname(ext_path))
            except OSError:
                pass

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
                        output = subprocess.check_output(args, env=env)
                    except subprocess.CalledProcessError as e:
                        pass

            # executables and win32(cygwin)-dll's need X bits
            if executable or sys.platform == "win32" or sys.platform == "cygwin":
                mode = os.stat(ext_path).st_mode
                mode |= (mode & 0o444) >> 2  # copy R bits to X
                os.chmod(ext_path, mode)

    def run(self):
        if not self.extensions:
            return

        all_optional = all(ext.optional for ext in self.extensions)
        try:
            version = get_rust_version()
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
                        "Rust %s does not match extension requirement %s"
                        % (version, ext.rust_version)
                    )

                self.build_extension(ext)
            except (
                DistutilsSetupError,
                DistutilsFileError,
                DistutilsExecError,
                DistutilsPlatformError,
                CompileError,
            ) as e:
                if not ext.optional:
                    raise
                else:
                    print("Build optional Rust extension %s failed." % ext.name)
                    print(str(e))
