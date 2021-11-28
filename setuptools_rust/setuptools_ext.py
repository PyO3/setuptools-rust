import os
import subprocess
import sys
from distutils import log
from distutils.command.clean import clean
from typing import List, Tuple, Type, cast

from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
from setuptools.command.sdist import sdist
from setuptools.dist import Distribution
from typing_extensions import Literal

from .extension import RustExtension

try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:
    bdist_wheel = None


def add_rust_extension(dist: Distribution) -> None:
    sdist_base_class = cast(Type[sdist], dist.cmdclass.get("sdist", sdist))
    sdist_options = sdist_base_class.user_options.copy()
    sdist_boolean_options = sdist_base_class.boolean_options.copy()
    sdist_negative_opt = sdist_base_class.negative_opt.copy()
    sdist_options.extend(
        [
            ("vendor-crates", None, "vendor Rust crates"),
            (
                "no-vendor-crates",
                None,
                "don't vendor Rust crates." "[default; enable with --vendor-crates]",
            ),
        ]
    )
    sdist_boolean_options.append("vendor-crates")
    sdist_negative_opt["no-vendor-crates"] = "vendor-crates"

    class sdist_rust_extension(sdist_base_class):  # type: ignore[misc,valid-type]
        user_options = sdist_options
        boolean_options = sdist_boolean_options
        negative_opt = sdist_negative_opt

        def initialize_options(self) -> None:
            super().initialize_options()
            self.vendor_crates = 0

        def make_distribution(self) -> None:
            if self.vendor_crates:
                manifest_paths = []
                for ext in self.distribution.rust_extensions:
                    manifest_paths.append(ext.path)
                if manifest_paths:
                    base_dir = self.distribution.get_fullname()
                    dot_cargo_path = os.path.join(base_dir, ".cargo")
                    self.mkpath(dot_cargo_path)
                    cargo_config_path = os.path.join(dot_cargo_path, "config.toml")
                    vendor_path = os.path.join(dot_cargo_path, "vendor")
                    command = ["cargo", "vendor"]
                    # additional Cargo.toml for extension 1..n
                    for extra_path in manifest_paths[1:]:
                        command.append("--sync")
                        command.append(extra_path)
                    # `cargo vendor --sync` accepts multiple values, for example
                    # `cargo vendor --sync a --sync b --sync c vendor_path`
                    # but it would also consider vendor_path as --sync value
                    # set --manifest-path before vendor_path and after --sync to workaround that
                    # See https://docs.rs/clap/latest/clap/struct.Arg.html#method.multiple for detail
                    command.extend(["--manifest-path", manifest_paths[0], vendor_path])
                    cargo_config = subprocess.check_output(command)
                    base_dir_bytes = (
                        base_dir.encode(sys.getfilesystemencoding()) + os.sep.encode()
                    )
                    if os.sep == "\\":
                        # TOML escapes backslash \
                        base_dir_bytes += os.sep.encode()
                    cargo_config = cargo_config.replace(base_dir_bytes, b"")
                    if os.altsep:
                        cargo_config = cargo_config.replace(
                            base_dir_bytes + os.altsep.encode(), b""
                        )

                    # Check whether `.cargo/config`/`.cargo/config.toml` already exists
                    existing_cargo_config = None
                    for filename in (
                        f".cargo{os.sep}config",
                        f".cargo{os.sep}config.toml",
                    ):
                        if filename in self.filelist.files:
                            existing_cargo_config = filename
                            break
                    if existing_cargo_config:
                        cargo_config_path = os.path.join(
                            base_dir, existing_cargo_config
                        )
                        # Append vendor config to original cargo config
                        with open(existing_cargo_config, "rb") as f:
                            cargo_config = f.read() + b"\n" + cargo_config

                    with open(cargo_config_path, "wb") as f:
                        f.write(cargo_config)
                    self.filelist.append(vendor_path)
                    self.filelist.append(cargo_config_path)
            super().make_distribution()

    dist.cmdclass["sdist"] = sdist_rust_extension

    build_ext_base_class = cast(
        Type[build_ext], dist.cmdclass.get("build_ext", build_ext)
    )
    build_ext_options = build_ext_base_class.user_options.copy()
    build_ext_options.append(("target", None, "Build for the target triple"))

    class build_ext_rust_extension(build_ext_base_class):  # type: ignore[misc,valid-type]
        user_options = build_ext_options

        def initialize_options(self) -> None:
            super().initialize_options()
            self.target = os.getenv("CARGO_BUILD_TARGET")

        def run(self) -> None:
            if self.distribution.rust_extensions:
                log.info("running build_rust")
                build_rust = self.get_finalized_command("build_rust")
                build_rust.inplace = self.inplace
                build_rust.target = self.target
                build_rust.verbose = self.verbose
                options = self.distribution.get_cmdline_options().get("bdist_wheel", {})
                plat_name = options.get("plat-name") or self.plat_name
                build_rust.plat_name = plat_name
                build_rust.run()

            build_ext_base_class.run(self)

    dist.cmdclass["build_ext"] = build_ext_rust_extension

    clean_base_class = cast(Type[clean], dist.cmdclass.get("clean", clean))

    class clean_rust_extension(clean_base_class):  # type: ignore[misc,valid-type]
        def run(self) -> None:
            clean_base_class.run(self)
            if not self.dry_run:
                self.run_command("clean_rust")

    dist.cmdclass["clean"] = clean_rust_extension

    install_base_class = cast(Type[install], dist.cmdclass.get("install", install))

    # this is required because, install directly access distribution's
    # ext_modules attr to check if dist has ext modules
    class install_rust_extension(install_base_class):  # type: ignore[misc,valid-type]
        def finalize_options(self) -> None:
            ext_modules = self.distribution.ext_modules

            # all ext modules
            mods = []
            if self.distribution.ext_modules:
                mods.extend(self.distribution.ext_modules)
            if self.distribution.rust_extensions:
                mods.extend(self.distribution.rust_extensions)

                scripts = []
                for ext in self.distribution.rust_extensions:
                    scripts.extend(ext.entry_points())

                if scripts:
                    if not self.distribution.entry_points:
                        self.distribution.entry_points = {"console_scripts": scripts}
                    else:
                        ep_scripts = self.distribution.entry_points.get(
                            "console_scripts"
                        )
                        if ep_scripts:
                            for script in scripts:
                                if script not in ep_scripts:
                                    ep_scripts.append(scripts)
                        else:
                            ep_scripts = scripts

                        self.distribution.entry_points["console_scripts"] = ep_scripts

            self.distribution.ext_modules = mods

            install_base_class.finalize_options(self)

            # restore ext_modules
            self.distribution.ext_modules = ext_modules

    dist.cmdclass["install"] = install_rust_extension

    if bdist_wheel is not None:
        bdist_wheel_base_class = cast(  # type: ignore[no-any-unimported]
            Type[bdist_wheel], dist.cmdclass.get("bdist_wheel", bdist_wheel)
        )
        bdist_wheel_options = bdist_wheel_base_class.user_options.copy()
        bdist_wheel_options.append(("target", None, "Build for the target triple"))

        # this is for console entries
        class bdist_wheel_rust_extension(bdist_wheel_base_class):  # type: ignore[misc,valid-type]
            user_options = bdist_wheel_options

            def initialize_options(self) -> None:
                super().initialize_options()
                self.target = os.getenv("CARGO_BUILD_TARGET")

            def finalize_options(self) -> None:
                scripts = []
                for ext in self.distribution.rust_extensions:
                    scripts.extend(ext.entry_points())

                if scripts:
                    if not self.distribution.entry_points:
                        self.distribution.entry_points = {"console_scripts": scripts}
                    else:
                        ep_scripts = self.distribution.entry_points.get(
                            "console_scripts"
                        )
                        if ep_scripts:
                            for script in scripts:
                                if script not in ep_scripts:
                                    ep_scripts.append(scripts)
                        else:
                            ep_scripts = scripts

                        self.distribution.entry_points["console_scripts"] = ep_scripts

                bdist_wheel_base_class.finalize_options(self)

            def get_tag(self) -> Tuple[str, str, str]:
                python, abi, plat = super().get_tag()
                arch_flags = os.getenv("ARCHFLAGS")
                universal2 = False
                if self.plat_name.startswith("macosx-") and arch_flags:
                    universal2 = "x86_64" in arch_flags and "arm64" in arch_flags
                if universal2 and plat.startswith("macosx_"):
                    from wheel.macosx_libfile import calculate_macosx_platform_tag

                    macos_target = os.getenv("MACOSX_DEPLOYMENT_TARGET")
                    if macos_target is None:
                        # Example: macosx_11_0_arm64
                        macos_target = ".".join(plat.split("_")[1:3])
                    plat = calculate_macosx_platform_tag(
                        self.bdist_dir, "macosx-{}-universal2".format(macos_target)
                    )
                return python, abi, plat

        dist.cmdclass["bdist_wheel"] = bdist_wheel_rust_extension


def patch_distutils_build() -> None:
    """Patch distutils to use `has_ext_modules()`

    See https://github.com/pypa/distutils/pull/43
    """
    from distutils.command import build as _build

    class build(_build.build):
        # Missing type def from distutils.cmd.Command; add it here for now
        distribution: Distribution

        def finalize_options(self) -> None:
            build_lib_user_specified = self.build_lib is not None
            super().finalize_options()
            if not build_lib_user_specified:
                if self.distribution.has_ext_modules():  # type: ignore[attr-defined]
                    self.build_lib = self.build_platlib
                else:
                    self.build_lib = self.build_purelib

    _build.build = build  # type: ignore[misc]


def rust_extensions(
    dist: Distribution, attr: Literal["rust_extensions"], value: List[RustExtension]
) -> None:
    assert attr == "rust_extensions"
    has_rust_extensions = len(value) > 0

    # Monkey patch has_ext_modules to include Rust extensions; pairs with
    # patch_distutils_build above.
    #
    # has_ext_modules is missing from Distribution typing.
    orig_has_ext_modules = dist.has_ext_modules  # type: ignore[attr-defined]
    dist.has_ext_modules = lambda: (orig_has_ext_modules() or has_rust_extensions)  # type: ignore[attr-defined]

    if has_rust_extensions:
        patch_distutils_build()
        add_rust_extension(dist)
