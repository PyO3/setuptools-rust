import os
import tarfile
from inspect import cleandoc as heredoc
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
    session.install(".", "build", "wheel")
    namespace_package = Path(__file__).parent / "examples" / "namespace_package"
    os.chdir(namespace_package)
    tmp = session.create_tmp()

    build_config = """
        [sdist]
        vendor_crates = True
        """
    Path(tmp, "setup.cfg").write_text(heredoc(build_config), encoding="utf-8")

    env = os.environ.copy()
    env.update(DIST_EXTRA_CONFIG=str(Path(tmp, "setup.cfg")))
    cmd = ["python", "-m", "build", "--sdist", "--no-isolation"]
    session.run(*cmd, env=env, external=True)

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
        session.run("print-hello")
        session.run("sum-cli", "5", "7")
        session.run("rust-demo", "5", "7")

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
    session.install(".", "build")
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
            cmd = ["python", "-m", "build", "--wheel", "--no-isolation"]
            session.run(*cmd, env=env, external=True)

        with session.chdir(emscripten_dir):
            session.run("node", "runner.js", str(example), external=True)


@nox.session(name="bump-version")
def bump_version(session: nox.Session) -> None:
    session.install("bump2version")
    session.run("bumpversion", *session.posargs)
