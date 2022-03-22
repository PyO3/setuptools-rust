from os.path import dirname

import nox

SETUPTOOLS_RUST = dirname(dirname(dirname(__file__)))


@nox.session()
def test(session: nox.Session):
    session.install(SETUPTOOLS_RUST, "pytest", "pytest-benchmark", "beautifulsoup4")
    session.install(".")
    session.run("pytest", *session.posargs)
