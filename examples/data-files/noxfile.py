from pathlib import Path

import nox

SETUPTOOLS_RUST = Path(__file__).parents[2]


@nox.session()
def test(session: nox.Session):
    session.install(str(SETUPTOOLS_RUST), "setuptools", "pytest")
    session.install("--no-build-isolation", ".")
    session.run("pytest", "tests", *session.posargs)


@nox.session()
def test_inplace(session: nox.Session):
    session.install(str(SETUPTOOLS_RUST), "setuptools", "pytest")
    session.install("--no-build-isolation", "--editable", ".")
    try:
        session.run("pytest", "tests", *session.posargs)
    finally:
        # Clear out any data files that _did_ exist
        session.run(
            "python",
            "-c",
            """
import os
import shutil
from pathlib import Path
import data_files

try:
    os.remove(Path(data_files.__file__).parent / "my_file.txt")
except FileNotFoundError:
    pass
shutil.rmtree(Path(data_files.__file__).parent / "_data", ignore_errors=True)""",
        )
