from os.path import dirname

import nox

SETUPTOOLS_RUST = dirname(dirname(dirname(__file__)))


@nox.session()
def test(session: nox.Session):
    session.install(SETUPTOOLS_RUST, "pytest")

    try:
        session.install("cffi", "--only-binary=cffi")
    except nox.command.CommandFailed:
        session.skip("cffi not available on this platform")

    # Ensure build uses version of setuptools-rust under development
    session.install("--no-build-isolation", ".")
    # Test Python package
    session.run("pytest", *session.posargs)
