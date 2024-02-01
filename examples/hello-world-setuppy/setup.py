from setuptools import find_packages, setup

from setuptools_rust import Binding, RustExtension

setup(
    name="hello-world",
    version="1.0",
    packages=find_packages(where="python"),
    package_dir={"": "python"},
    rust_extensions=[
        RustExtension(
            "hello_world._lib",
            # ^-- The last part of the name (e.g. "_lib") has to match lib.name
            #     in Cargo.toml and the function name in the `.rs` file,
            #     but you can add a prefix to nest it inside of a Python package.
            path="Cargo.toml",  # Default value, can be omitted
            binding=Binding.PyO3,  # Default value, can be omitted
        )
    ],
    # rust extensions are not zip safe, just like C-extensions.
    # But `zip_safe=False` is an obsolete config that does not affect how `pip`
    # or `importlib.{resources,metadata}` handle the package.
)
# See reference for RustExtension in https://setuptools-rust.readthedocs.io/en/latest/reference.html
