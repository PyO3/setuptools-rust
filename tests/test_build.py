from unittest import mock

from setuptools_rust.build import _adjusted_local_rust_target


def test_adjusted_local_rust_target_windows_msvc():
    with mock.patch(
        "setuptools_rust.rustc_info.get_rust_target_info", lambda _: ["target_env=msvc"]
    ):
        assert _adjusted_local_rust_target("win32") == "i686-pc-windows-msvc"
        assert _adjusted_local_rust_target("win-amd64") == "x86_64-pc-windows-msvc"


def test_adjusted_local_rust_target_windows_gnu():
    with mock.patch(
        "setuptools_rust.rustc_info.get_rust_target_info", lambda _: ["target_env=gnu"]
    ):
        assert _adjusted_local_rust_target("win32") == "i686-pc-windows-gnu"
        assert _adjusted_local_rust_target("win-amd64") == "x86_64-pc-windows-gnu"


def test_adjusted_local_rust_target_windows_gnu():
    with mock.patch("platform.machine", lambda: "x86_64"):
        assert _adjusted_local_rust_target("macosx-") == "x86_64-apple-darwin"
