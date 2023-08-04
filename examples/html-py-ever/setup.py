#!/usr/bin/env python

from setuptools import find_packages, setup

from setuptools_rust import RustExtension

setup(
    packages=find_packages(where="python"),
    package_dir={"": "python"},
    rust_extensions=[RustExtension("html_py_ever.html_py_ever")],
)
