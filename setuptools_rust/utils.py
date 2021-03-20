import os
import subprocess
from distutils.errors import DistutilsPlatformError
from typing import List, Optional, Set, Tuple, Union

from semantic_version import Version
from typing_extensions import Literal

from .extension import Binding, RustExtension

PyLimitedApi = Literal["cp36", "cp37", "cp38", "cp39", True, False]


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


def get_rust_version() -> Optional[Version]:  # type: ignore[no-any-unimported]
    try:
        output = subprocess.check_output(["rustc", "-V"]).decode("latin-1")
        return Version(output.split(" ")[1])
    except (subprocess.CalledProcessError, OSError):
        return None


def get_rust_target_info(target_triple: Optional[str] = None) -> List[str]:
    cmd = ["rustc", "--print", "cfg"]
    if target_triple:
        cmd.extend(["--target", target_triple])
    output = subprocess.check_output(cmd, universal_newlines=True)
    return output.splitlines()


_rust_target_list = None


def get_rust_target_list() -> List[str]:
    global _rust_target_list
    if _rust_target_list is None:
        output = subprocess.check_output(
            ["rustc", "--print", "target-list"], universal_newlines=True
        )
        _rust_target_list = output.splitlines()
    return _rust_target_list


def split_platform_and_extension(ext_path: str) -> Tuple[str, str, str]:
    """Splits an extension path into a tuple (ext_path, plat_tag, extension).

    >>> split_platform_and_extension("foo/bar.platform.so")
    ('foo/bar', '.platform', '.so')
    """

    # rust.cpython-38-x86_64-linux-gnu.so to (rust.cpython-38-x86_64-linux-gnu, .so)
    ext_path, extension = os.path.splitext(ext_path)
    # rust.cpython-38-x86_64-linux-gnu to (rust, .cpython-38-x86_64-linux-gnu)
    ext_path, platform_tag = os.path.splitext(ext_path)
    return (ext_path, platform_tag, extension)
