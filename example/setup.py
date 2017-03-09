from setuptools import setup
from setuptools_rust import RustExtension


setup(name='hello-rust',
      version='1.0',
      rust_extensions=[
          RustExtension('hello_rust._helloworld', 'extensions/Cargo.toml')],
      packages=['hello_rust'],
      # rust extensions are not zip safe, just like C-extensions.
      zip_safe=False)
