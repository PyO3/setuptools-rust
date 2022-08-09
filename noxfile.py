import os
import sys
import tarfile
from glob import glob
from pathlib import Path
from unittest.mock import patch

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


@nox.session(name="test-mingw")
def test_mingw(session: nox.Session):
    # manually re-implemented test-examples to workaround
    # https://github.com/wntrblm/nox/issues/630

    oldrun = nox.command.run

    def newrun(*args, **kwargs):
        # suppress "external" error on install
        kwargs["external"] = True
        oldrun(*args, **kwargs)

    def chdir(path: Path):
        print(path)
        os.chdir(path)

    examples = Path(os.path.dirname(__file__)).absolute() / "examples"

    with patch.object(nox.command, "run", newrun):
        session.install(".")

        session.install("--no-build-isolation", str(examples / "hello-world"))
        session.run("hello-world")

        session.install("pytest", "pytest-benchmark", "beautifulsoup4")
        session.install("--no-build-isolation", str(examples / "html-py-ever"))
        session.run("pytest", str(examples / "html-py-ever"))

        session.install("pytest")
        session.install("--no-build-isolation", str(examples / "html-py-ever"))
        session.run("pytest", str(examples / "html-py-ever"))

        session.install("pytest", "cffi")
        session.install("--no-build-isolation", str(examples / "html-py-ever"))
        session.run("pytest", str(examples / "html-py-ever"))


@nox.session(name="test-examples-emscripten")
def test_examples_emscripten(session: nox.Session):
    session.install(".")
    emscripten_dir = Path("./emscripten").resolve()

    session.run(
        "rustup",
        "component",
        "add",
        "rust-src",
        "--toolchain",
        "nightly",
        external=True,
    )
    examples_dir = Path("examples").absolute()
    test_crates = [
        examples_dir / "html-py-ever",
        examples_dir / "namespace_package",
    ]
    for example in test_crates:
        env = os.environ.copy()
        env.update(
            RUSTUP_TOOLCHAIN="nightly",
            PYTHONPATH=str(emscripten_dir),
            _PYTHON_SYSCONFIGDATA_NAME="_sysconfigdata__emscripten_wasm32-emscripten",
            _PYTHON_HOST_PLATFORM="emscripten_3_1_14_wasm32",
            CARGO_BUILD_TARGET="wasm32-unknown-emscripten",
            CARGO_TARGET_WASM32_UNKNOWN_EMSCRIPTEN_LINKER=str(
                emscripten_dir / "emcc_wrapper.py"
            ),
            PYO3_CONFIG_FILE=str(emscripten_dir / "pyo3_config.ini"),
        )
        with session.chdir(example):
            session.run("python", "setup.py", "bdist_wheel", env=env, external=True)

        with session.chdir(emscripten_dir):
            session.run("node", "runner.js", str(example), external=True)


@nox.session(name="bump-version")
def bump_version(session: nox.Session) -> None:
    session.install("bump2version")
    session.run("bumpversion", *session.posargs)
