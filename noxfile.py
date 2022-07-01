import os
import tarfile
from glob import glob
from pathlib import Path

import nox


@nox.session(name="test-examples", venv_backend="none")
def test_examples(session: nox.Session):
    for example in glob("examples/*/noxfile.py"):
        session.run("nox", "-f", example, external=True)


@nox.session(name="test-sdist-vendor")
def test_sdist_vendor(session: nox.Session):
    session.install(".")
    namespace_package = Path(__file__).parent / "examples" / "namespace_package"
    os.chdir(namespace_package)
    session.run("python", "setup.py", "sdist", "--vendor-crates", external=True)
    dist = namespace_package / "dist"
    with tarfile.open(str(dist / "namespace_package-0.1.0.tar.gz")) as tf:
        tf.extractall(str(dist))
    os.chdir(dist / "namespace_package-0.1.0")
    session.run("cargo", "build", "--offline", external=True)


@nox.session()
def mypy(session: nox.Session):
    session.install("mypy", "fat_macho", "types-setuptools", ".")
    session.run("mypy", "setuptools_rust", *session.posargs)


@nox.session()
def test(session: nox.Session):
    session.install("pytest", ".")
    session.run("pytest", "setuptools_rust", "tests", *session.posargs)
