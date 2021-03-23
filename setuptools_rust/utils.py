import subprocess
from distutils.errors import DistutilsPlatformError
from typing import Set, Union
from typing_extensions import Literal

import semantic_version

from .extension import Binding, RustExtension


def binding_features(
    ext: RustExtension,
    py_limited_api: Union[Literal["cp36", "cp37", "cp38", "cp39"], bool],
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


def get_rust_version(min_version=None):
    try:
        output = subprocess.check_output(["rustc", "-V"]).decode("latin-1")
        return semantic_version.Version(output.split(" ")[1], partial=True)
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


def get_rust_target_info():
    output = subprocess.check_output(["rustc", "--print", "cfg"])
    return output.splitlines()
