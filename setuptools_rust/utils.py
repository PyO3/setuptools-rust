from __future__ import print_function, absolute_import
import sys
import subprocess
from distutils.errors import DistutilsPlatformError

import semantic_version


class Binding:
    """
    Binding Options
    """
    #  https://github.com/PyO3/PyO3
    PyO3 = 0
    #  https://github.com/dgrunwald/rust-cpython
    RustCPython = 1
    #  Bring your own binding
    NoBinding = 2


def cpython_feature(ext=True, binding=Binding.PyO3):
    version = sys.version_info

    if binding is Binding.NoBinding:
        return ()
    elif binding is Binding.PyO3:
        if (2, 7) < version < (2, 8):
            if ext:
                return ("pyo3/python2", "pyo3/extension-module")
            else:
                return ("pyo3/python2",)
        elif version > (3, 4):
            if ext:
                return ("pyo3/python3", "pyo3/extension-module")
            else:
                return ("pyo3/python3",)
        else:
            raise DistutilsPlatformError("Unsupported python version: %s" % sys.version)
    elif binding is Binding.RustCPython:
        if (2, 7) < version < (2, 8):
            if ext:
                return ("cpython/python27-sys", "cpython/extension-module-2-7")
            else:
                return ("cpython/python27-sys",)
        elif (3, 3) < version:
            if ext:
                return ("cpython/python3-sys", "cpython/extension-module")
            else:
                return ("cpython/python3-sys",)
        else:
            raise DistutilsPlatformError(
                "Unsupported python version: %s" % sys.version)
    else:
        raise DistutilsPlatformError('Unknown Binding: "{}" '.format(binding))

def get_rust_version():
    try:
        output = subprocess.check_output(["rustc", "-V"])
        if isinstance(output, bytes):
            output = output.decode('latin-1')
        return semantic_version.Version(output.split(' ')[1], partial=True)
    except (subprocess.CalledProcessError, OSError):
        raise DistutilsPlatformError('Can not find Rust compiler')
    except Exception as exc:
        raise DistutilsPlatformError(
            'Can not get rustc version: %s' % str(exc))
