from setuptools import setup

from setuptools_rust import RustBin

setup(
    name="hello-world",
    version="1.0",
    rust_extensions=[
        RustBin(
            "hello-world",
            args=["--profile", "release-lto"],
        )
    ],
    # rust extensions are not zip safe, just like C-extensions.
    zip_safe=False,
)
