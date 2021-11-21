from setuptools import setup

from setuptools_rust import Binding, RustExtension

setup(
    name="hello-world",
    version="1.0",
    rust_extensions=[
        RustExtension(
            {"hello-world": "hello_world.hello_world"},
            binding=Binding.Exec,
            script=True,
        )
    ],
    # rust extensions are not zip safe, just like C-extensions.
    zip_safe=False,
)
