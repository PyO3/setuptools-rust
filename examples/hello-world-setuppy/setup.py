from setuptools import find_packages, setup

from setuptools_rust import RustBin

setup(
    name="hello-world",
    version="1.0",
    packages=find_packages(where="python"),
    package_dir={"": "python"},
    rust_extensions=[
        RustBin(
            "hello-world",
            args=["--profile", "release-lto"],
        )
    ],
    # rust extensions are not zip safe, just like C-extensions.
    zip_safe=False,
)
