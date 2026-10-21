import sysconfig
from pathlib import Path
from unittest import mock

import pytest
from setuptools import Distribution

from setuptools_rust._utils import Env
from setuptools_rust.build import _override_cargo_default_target, build_rust
from setuptools_rust.extension import RustExtension

NO_ENV = Env(None)


def test_override_cargo_default_target_windows_msvc():
    with mock.patch(
        "setuptools_rust.rustc_info.get_rust_target_info",
        lambda _plat_name, _env: ["target_env=msvc"],
    ):
        assert _override_cargo_default_target("win32", NO_ENV) == "i686-pc-windows-msvc"
        assert (
            _override_cargo_default_target("win-amd64", NO_ENV)
            == "x86_64-pc-windows-msvc"
        )


def test_adjusted_local_rust_target_windows_gnu():
    with mock.patch(
        "setuptools_rust.rustc_info.get_rust_target_info",
        lambda _plat_name, _env: ["target_env=gnu"],
    ):
        assert _override_cargo_default_target("win32", NO_ENV) == "i686-pc-windows-gnu"
        assert (
            _override_cargo_default_target("win-amd64", NO_ENV)
            == "x86_64-pc-windows-gnu"
        )


def test_adjusted_local_rust_target_macos():
    with mock.patch("platform.machine", lambda: "x86_64"):
        assert (
            _override_cargo_default_target("macosx-", NO_ENV) == "x86_64-apple-darwin"
        )


@pytest.mark.parametrize(
    "ext_suffix",
    [None, "", ".so", ".custom.so", ".custom.extension.suffix.longer.than.default.so"],
)
@pytest.mark.parametrize(
    "abi3_suffix",
    [
        None,
        ".abi3.so",
        ".abi3-aarch64-linux-gnu.so",
        ".abi3t-aarch64-linux-gnu.so",
        ".pyd",
    ],
)
def test_get_dylib_ext_path_suffix_override(monkeypatch, ext_suffix, abi3_suffix):
    if ext_suffix is None:
        monkeypatch.delenv("SETUPTOOLS_EXT_SUFFIX", raising=False)
    else:
        monkeypatch.setenv("SETUPTOOLS_EXT_SUFFIX", ext_suffix)
    ext = RustExtension("package.rust")
    command = build_rust(Distribution())
    command.plat_name = sysconfig.get_platform()
    build_ext = command.get_finalized_command("build_ext")
    path = Path(build_ext.get_ext_fullpath(ext.name))
    expected = path.with_name("rust" + abi3_suffix) if abi3_suffix else path
    with (
        mock.patch.object(command, "_py_limited_api", return_value="cp39"),
        mock.patch("setuptools_rust.build.get_abi3_suffix", return_value=abi3_suffix),
    ):
        assert Path(command.get_dylib_ext_path(ext, ext.name)) == expected
