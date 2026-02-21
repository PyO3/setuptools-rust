from unittest import mock

from setuptools_rust.build import _override_cargo_default_target
from setuptools_rust._utils import Env


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
