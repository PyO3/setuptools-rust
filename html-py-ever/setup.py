#!/usr/bin/env python
import sys

from setuptools import setup
from setuptools_rust import RustExtension

setup(
    name="html-py-ever",
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
    packages=["html_py_ever"],
    install_requires=[
        "beautifulsoup4",
        "lxml"
    ],
    rust_extensions=[RustExtension("html_py_ever.html_py_ever")],
    include_package_data=True,
    zip_safe=False,
)
