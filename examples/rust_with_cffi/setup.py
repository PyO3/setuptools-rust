#!/usr/bin/env python
from setuptools import find_packages, setup
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
    packages=find_packages(where="python"),
    package_dir={"": "python"},
    rust_extensions=[
        RustExtension("rust_with_cffi.rust"),
    ],
    cffi_modules=["cffi_module.py:ffi"],
    install_requires=["cffi"],
    include_package_data=True,
    zip_safe=False,
)
