from os.path import dirname

import nox

SETUPTOOLS_RUST = dirname(dirname(dirname(__file__)))


@nox.session()
def test(session: nox.Session):
    session.install(SETUPTOOLS_RUST, "wheel", "build", "pytest")
    # Ensure build works as intended
    session.install("--no-build-isolation", ".")
    # Test Rust binary
    session.run("print-hello")
    # Test script wrapper for Python entry-point
    session.run("sum-cli", "5", "7")
    session.run("rust-demo", "5", "7")
    # Test library
    session.run("pytest", "tests", *session.posargs)
    session.run("python", "-c", "from hello_world import _lib; print(_lib)")
