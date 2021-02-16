import platform

from setuptools import setup, find_namespace_packages
from setuptools_rust import Binding, RustExtension


setup(
    name='universal2',
    version="0.1.0",
    packages=find_namespace_packages(include=['universal2.*']),
    zip_safe=False,
    rust_extensions=[RustExtension(
        "universal2.rust",
        path="Cargo.toml",
        binding=Binding.PyO3,
        debug=False,
        py_limited_api=True,
        features=[] if platform.python_implementation() == 'PyPy' else ["pyo3/abi3"],
        universal2=True
    )],
)
