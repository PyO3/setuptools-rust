import subprocess
import sys
from pathlib import Path

from setuptools import build_meta as _setuptools_build_meta

_ROOT = Path(__file__).parent


def _generate_cffi_source():
    """Generate the CFFI source file from the Python module.

    `cffi` provides a command line tool `gen_src` that can be used to
    generate the C source file from a Python module that defines the
    CFFI interface.

    By implementing an in-tree build backend, we can invoke this before
    forwarding to regular setuptools build backend functions.
    """

    # cffi documents `gen_src` as a command line tool
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "cffi.gen_src",
            "exec-python",
            "--ffi-var=ffi",
            "cffi_module.py",
            "cffi_module.c",
        ],
        cwd=_ROOT,
    )


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    _generate_cffi_source()
    return _setuptools_build_meta.build_wheel(
        wheel_directory, config_settings, metadata_directory
    )


def build_sdist(sdist_directory, config_settings=None):
    _generate_cffi_source()
    return _setuptools_build_meta.build_sdist(sdist_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    _generate_cffi_source()
    return _setuptools_build_meta.build_editable(
        wheel_directory, config_settings, metadata_directory
    )


get_requires_for_build_wheel = _setuptools_build_meta.get_requires_for_build_wheel
get_requires_for_build_sdist = _setuptools_build_meta.get_requires_for_build_sdist
get_requires_for_build_editable = _setuptools_build_meta.get_requires_for_build_editable
prepare_metadata_for_build_wheel = (
    _setuptools_build_meta.prepare_metadata_for_build_wheel
)
prepare_metadata_for_build_editable = (
    _setuptools_build_meta.prepare_metadata_for_build_editable
)
