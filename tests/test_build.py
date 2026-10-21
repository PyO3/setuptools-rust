from unittest import mock

import pytest

from setuptools_rust._utils import Env
from setuptools_rust.build import _binding_features, _override_cargo_default_target
from setuptools_rust.extension import Binding, RustExtension

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
    "gil_disabled,py_limited_api,feature",
    [
        (None, "cp315", "abi3-py315"),
        (0, False, None),
        (0, True, "abi3"),
        (0, "cp39", "abi3-py39"),
        (0, "cp315", "abi3-py315"),
        (1, False, None),
        (1, True, "abi3t"),
        (1, "cp315", "abi3t-py315"),
        (1, "cp316", "abi3t-py316"),
    ],
)
def test_binding_features_target_abi(gil_disabled, py_limited_api, feature):
    ext = RustExtension("test")
    with mock.patch(
        "setuptools_rust.build.get_config_var", return_value=gil_disabled
    ) as get_config_var:
        features = _binding_features(ext, py_limited_api)
    get_config_var.assert_called_once_with("Py_GIL_DISABLED")
    expected = {"pyo3/extension-module"}
    if feature is not None:
        expected.add(f"pyo3/{feature}")
    assert features == expected


@pytest.mark.parametrize("py_limited_api", [True, False])
def test_binding_features_explicit_limited_api(py_limited_api):
    with pytest.warns(DeprecationWarning, match="RustExtension.py_limited_api"):
        ext = RustExtension("test", py_limited_api=py_limited_api)
    with mock.patch("setuptools_rust.build.get_config_var") as get_config_var:
        assert _binding_features(ext, "cp315") == {"pyo3/extension-module"}
    get_config_var.assert_not_called()


@pytest.mark.parametrize(
    "binding,expected",
    [
        (Binding.NoBinding, set()),
        (Binding.Exec, set()),
        (Binding.RustCPython, {"cpython/python3-sys", "cpython/extension-module"}),
    ],
)
def test_binding_features_other_bindings(binding, expected):
    ext = RustExtension("test", binding=binding)
    with mock.patch("setuptools_rust.build.get_config_var") as get_config_var:
        assert _binding_features(ext, "cp315") == expected
    get_config_var.assert_not_called()
