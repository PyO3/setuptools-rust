import os
import subprocess
import sysconfig
from distutils import log
from distutils.command.clean import clean
from typing import List, Set, Tuple, Type, cast

from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
from setuptools.command.install_lib import install_lib
from setuptools.command.install_scripts import install_scripts
from setuptools.command.sdist import sdist
from setuptools.dist import Distribution
from typing_extensions import Literal

from .extension import RustBin, RustExtension

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

    # Patch dist to include console_scripts for Exec binding
    console_scripts = []
    for ext in dist.rust_extensions:  # type: ignore[attr-defined]
        console_scripts.extend(ext.entry_points())

    if console_scripts:
        if not dist.entry_points:  # type: ignore[attr-defined]
            dist.entry_points = {"console_scripts": console_scripts}  # type: ignore[attr-defined]
        else:
            ep_scripts = dist.entry_points.get("console_scripts")  # type: ignore[attr-defined]
            if ep_scripts:
                for script in console_scripts:
                    if script not in ep_scripts:
                        ep_scripts.append(console_scripts)
            else:
                ep_scripts = console_scripts

            dist.entry_points["console_scripts"] = ep_scripts  # type: ignore[attr-defined]

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

                # Collate cargo manifest options together.
                # We can cheat here, as the only valid options are the simple strings
                # --frozen, --locked, or --offline.
                #
                # https://doc.rust-lang.org/cargo/commands/cargo-build.html#manifest-options
                cargo_manifest_args: Set[str] = set()
                for ext in self.distribution.rust_extensions:
                    manifest_paths.append(ext.path)
                    if ext.cargo_manifest_args:
                        cargo_manifest_args.update(ext.cargo_manifest_args)

                if manifest_paths:
                    base_dir = self.distribution.get_fullname()
                    dot_cargo_path = os.path.join(base_dir, ".cargo")
                    self.mkpath(dot_cargo_path)
                    cargo_config_path = os.path.join(dot_cargo_path, "config.toml")
                    vendor_path = os.path.join(dot_cargo_path, "vendor")
                    command = ["cargo", "vendor"]
                    if cargo_manifest_args:
                        command.extend(sorted(cargo_manifest_args))
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
                    subprocess.run(command, check=True)

                    cargo_config = _CARGO_VENDOR_CONFIG

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
                            cargo_config += f.read() + b"\n"

                    with open(cargo_config_path, "wb") as f:
                        f.write(cargo_config)

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

    # this is required to make install_scripts compatible with RustBin
    class install_rust_extension(install_base_class):  # type: ignore[misc,valid-type]
        def run(self) -> None:
            install_base_class.run(self)
            install_rustbin = False
            if self.distribution.rust_extensions:
                install_rustbin = any(
                    isinstance(ext, RustBin)
                    for ext in self.distribution.rust_extensions
                )
            if install_rustbin:
                self.run_command("install_scripts")

    dist.cmdclass["install"] = install_rust_extension

    install_lib_base_class = cast(
        Type[install_lib], dist.cmdclass.get("install_lib", install_lib)
    )

    # prevent RustBin from being installed to data_dir
    class install_lib_rust_extension(install_lib_base_class):  # type: ignore[misc,valid-type]
        def get_exclusions(self) -> Set[str]:
            exclusions: Set[str] = install_lib_base_class.get_exclusions(self)
            build_rust = self.get_finalized_command("build_rust")
            scripts_path = os.path.join(
                self.install_dir, build_rust.data_dir, "scripts"
            )
            if self.distribution.rust_extensions:
                exe = sysconfig.get_config_var("EXE")
                for ext in self.distribution.rust_extensions:
                    executable_name = ext.name
                    if exe is not None:
                        executable_name += exe
                    if isinstance(ext, RustBin):
                        exclusions.add(os.path.join(scripts_path, executable_name))
            return exclusions

    dist.cmdclass["install_lib"] = install_lib_rust_extension

    install_scripts_base_class = cast(
        Type[install_scripts], dist.cmdclass.get("install_scripts", install_scripts)
    )

    # this is required to make install_scripts compatible with RustBin
    class install_scripts_rust_extension(install_scripts_base_class):  # type: ignore[misc,valid-type]
        def run(self) -> None:
            install_scripts_base_class.run(self)
            build_ext = self.get_finalized_command("build_ext")
            build_rust = self.get_finalized_command("build_rust")
            scripts_path = os.path.join(
                build_ext.build_lib, build_rust.data_dir, "scripts"
            )
            if os.path.isdir(scripts_path):
                for file in os.listdir(scripts_path):
                    script_path = os.path.join(scripts_path, file)
                    if os.path.isfile(script_path):
                        with open(os.path.join(script_path), "rb") as script_reader:
                            self.write_script(file, script_reader.read(), mode="b")

    dist.cmdclass["install_scripts"] = install_scripts_rust_extension

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


def rust_extensions(
    dist: Distribution, attr: Literal["rust_extensions"], value: List[RustExtension]
) -> None:
    assert attr == "rust_extensions"
    has_rust_extensions = len(value) > 0

    # Monkey patch has_ext_modules to include Rust extensions.
    #
    # has_ext_modules is missing from Distribution typing.
    orig_has_ext_modules = dist.has_ext_modules  # type: ignore[attr-defined]
    dist.has_ext_modules = lambda: (orig_has_ext_modules() or has_rust_extensions)  # type: ignore[attr-defined]

    if has_rust_extensions:
        add_rust_extension(dist)


_CARGO_VENDOR_CONFIG = b"""
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = ".cargo/vendor"
"""
