from setuptools import setup

from setuptools_rust import Binding, RustExtension

setup(
    name="hello-world",
    version="1.0",
    rust_extensions=[
        RustExtension(
            {"hello-world": "hello_world.hello-world"},
            binding=Binding.Exec,
            script=True,
            args=["--profile", "release-lto"],
        )
    ],
    # rust extensions are not zip safe, just like C-extensions.
    zip_safe=False,
)
