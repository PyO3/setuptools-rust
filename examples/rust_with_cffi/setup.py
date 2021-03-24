#!/usr/bin/env python
import platform
import sys

from setuptools import setup
from setuptools_rust import RustExtension

setup(
    name="rust-with-cffi",
    version="0.1.0",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Rust",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
    ],
    packages=["rust_with_cffi"],
    rust_extensions=[
        RustExtension("rust_with_cffi.rust", py_limited_api="auto"),
    ],
    cffi_modules=["cffi_module.py:ffi"],
    install_requires=["cffi"],
    setup_requires=["cffi"],
    include_package_data=True,
    zip_safe=False,
)
