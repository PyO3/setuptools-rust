from os.path import dirname

import nox

SETUPTOOLS_RUST = dirname(dirname(dirname(__file__)))


@nox.session()
def test(session: nox.Session):
    session.install(SETUPTOOLS_RUST, "wheel", "pytest", "cffi")
    # Ensure build uses version of setuptools-rust under development
    session.install("--no-build-isolation", ".")
    # Test Python package
    session.run("pytest", *session.posargs)
