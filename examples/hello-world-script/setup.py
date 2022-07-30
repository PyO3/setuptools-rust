from setuptools import setup

from setuptools_rust import RustExtension, Binding

setup(
    name="hello-world-script",
    version="1.0",
    rust_extensions=[
        RustExtension(
            {"hello-world-script": "hello_world.hello-world-script"},
            binding=Binding.Exec,
            script=True,
            args=["--profile", "release-lto"],
        )
    ],
    # rust extensions are not zip safe, just like C-extensions.
    zip_safe=False,
)
