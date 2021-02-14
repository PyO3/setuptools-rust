import sys
import subprocess
from enum import IntEnum
from distutils.errors import DistutilsPlatformError

import semantic_version


class Binding(IntEnum):
    """
    Binding Options
    """
    # https://github.com/PyO3/PyO3
    PyO3 = 0
    # https://github.com/dgrunwald/rust-cpython
    RustCPython = 1
    # Bring your own binding
    NoBinding = 2
    # Build executable
    Exec = 3


class Strip(IntEnum):
    """
    Strip Options
    """
    # do not strip symbols
    No = 0
    # strip debug symbols
    Debug = 1
    # strip all symbos
    All = 2


def rust_features(ext=True, binding=Binding.PyO3):
    version = sys.version_info

    if binding in (Binding.NoBinding, Binding.Exec):
        return ()
    elif binding is Binding.PyO3:
        if version >= (3, 6):
            if ext:
                return {"pyo3/extension-module"}
            else:
                return {}
        else:
            raise DistutilsPlatformError(f"unsupported python version: {sys.version}")
    elif binding is Binding.RustCPython:
        if (3, 3) < version:
            if ext:
                return {"cpython/python3-sys", "cpython/extension-module"}
            else:
                return {"cpython/python3-sys"}
        else:
            raise DistutilsPlatformError(f"unsupported python version: {sys.version}")
    else:
        raise DistutilsPlatformError(f"unknown Rust binding: '{binding}'")


def get_rust_version():
    try:
        output = subprocess.check_output(["rustc", "-V"]).decode("latin-1")
        return semantic_version.Version(output.split(" ")[1], partial=True)
    except (subprocess.CalledProcessError, OSError):
        raise DistutilsPlatformError("can't find Rust compiler")
    except Exception as exc:
        raise DistutilsPlatformError(f"can't get rustc version: {str(exc)}")


def get_rust_target_info():
    output = subprocess.check_output(["rustc", "--print", "cfg"])
    return output.splitlines()
