import subprocess
from distutils.errors import DistutilsPlatformError
from typing import Set, Union

from packaging.version import Version
from typing_extensions import Literal

from .extension import Binding, RustExtension

PyLimitedApi = Union[Literal["cp36", "cp37", "cp38", "cp39"], bool]


def binding_features(
    ext: RustExtension,
    py_limited_api: PyLimitedApi,
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
                features.add(f"pyo3/abi3")
        return features
    elif ext.binding is Binding.RustCPython:
        return {"cpython/python3-sys", "cpython/extension-module"}
    else:
        raise DistutilsPlatformError(f"unknown Rust binding: '{ext.binding}'")


def _parse_rustc_version(rustc_output):
    """Parse output of ``rustc -V``

    >>> _parse_rustc_version("rustc 1.53.0 (53cb7b09b 2021-06-17)")
    <Version('1.53.0')>
    >>> _parse_rustc_version("rustc 1.53.0 (Fedora 1.53.0-1.fc34)")
    <Version('1.53.0')>
    >>> _parse_rustc_version("rustc 1.55.0-beta.1 (739f8f0a8 2021-07-28)")
    <Version('1.55.0b1')>
    >>> _parse_rustc_version("rustc 1.56.0-nightly (b70888601 2021-07-28)")
    <Version('1.56.0.dev0')>
    """
    version_string = rustc_output.split(" ")[1]
    # map nightly suffix to PEP 440-compatible .dev0 suffix
    if version_string.endswith("-nightly"):
        version_string = version_string[:-8] + ".dev0"
    return Version(version_string)


def get_rust_version(min_version=None):
    try:
        output = subprocess.check_output(["rustc", "-V"]).decode("latin-1")
        return _parse_rustc_version(output)
    except (subprocess.CalledProcessError, OSError):
        raise DistutilsPlatformError(
            "can't find Rust compiler\n\n"
            "If you are using an outdated pip version, it is possible a "
            "prebuilt wheel is available for this package but pip is not able "
            "to install from it. Installing from the wheel would avoid the "
            "need for a Rust compiler.\n\n"
            "To update pip, run:\n\n"
            "    pip install --upgrade pip\n\n"
            "and then retry package installation.\n\n"
            "If you did intend to build this package from source, try "
            "installing a Rust compiler from your system package manager and "
            "ensure it is on the PATH during installation. Alternatively, "
            "rustup (available at https://rustup.rs) is the recommended way "
            "to download and update the Rust compiler toolchain."
            + (
                f"\n\nThis package requires Rust {min_version}."
                if min_version is not None
                else ""
            )
        )
    except Exception as exc:
        raise DistutilsPlatformError(f"can't get rustc version: {str(exc)}")


def get_rust_target_info(target_triple=None):
    cmd = ["rustc", "--print", "cfg"]
    if target_triple:
        cmd.extend(["--target", target_triple])
    output = subprocess.check_output(cmd)
    return output.splitlines()


_rust_target_list = None


def get_rust_target_list():
    global _rust_target_list
    if _rust_target_list is None:
        output = subprocess.check_output(
            ["rustc", "--print", "target-list"], universal_newlines=True
        )
        _rust_target_list = output.splitlines()
    return _rust_target_list
