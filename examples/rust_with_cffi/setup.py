#!/usr/bin/env python
import sys

from setuptools import setup

from setuptools_rust import RustExtension

setup_requires = ["setuptools-rust>=0.10.1", "wheel", "cffi"]
install_requires = ["cffi"]

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
    rust_extensions=[RustExtension("rust_with_cffi.rust")],
    cffi_modules=["cffi_module.py:ffi"],
    install_requires=install_requires,
    setup_requires=setup_requires,
    include_package_data=True,
    zip_safe=False,
)
