import os
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
    tmp = Path(session.create_tmp())
    extra_config = tmp / "setup.cfg"

    build_config = """
        [sdist]
        vendor_crates = True
        """
    extra_config.write_text(heredoc(build_config), encoding="utf-8")

    env = os.environ.copy()
    env.update(DIST_EXTRA_CONFIG=str(extra_config))
    cmd = ["python", "-m", "build", "--sdist", "--no-isolation"]
    session.run(*cmd, env=env, external=True)

    session.run(
        "python",
        "-m",
        "pip",
        "install",
        Path("dist") / "namespace_package-0.1.0.tar.gz[dev]",
        "--no-build-isolation",
        "-v",
        # run in offline mode with a blank cargo home to prove the vendored
        # dependencies are sufficient to build the package
        env={"CARGO_NET_OFFLINE": "true", "CARGO_HOME": str(tmp / ".cargo")},
    )
    session.run("pytest")


@nox.session(name="test-crossenv", venv_backend=None)
def test_crossenv(session: nox.Session):
    try:
        arch = session.posargs[0]
    except IndexError:
        arch = "aarch64"
    print(arch)

    if arch == "aarch64":
        rust_target = "aarch64-unknown-linux-gnu"
        docker_platform = "aarch64"
    elif arch == "armv7":
        rust_target = "armv7-unknown-linux-gnueabihf"
        docker_platform = "linux/arm/v7"
    else:
        raise RuntimeError("don't know rust target for arch: " + arch)

    script_build = f"""set -ex
curl -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
source ~/.cargo/env
rustup target add {rust_target}

# https://github.com/pypa/setuptools_scm/issues/707
git config --global --add safe.directory /io

cd examples/rust_with_cffi/
# Using crossenv master to workaround https://github.com/benfogle/crossenv/issues/108, will need 1.5.0 when released
python3.11 -m pip install https://github.com/benfogle/crossenv/archive/refs/heads/master.zip
python3.11 -m crossenv "/opt/python/cp311-cp311/bin/python3" --cc $TARGET_CC --cxx $TARGET_CXX --sysroot $TARGET_SYSROOT --env LIBRARY_PATH= --manylinux manylinux1 /venv
. /venv/bin/activate

build-pip install -U 'pip>=23.2.1' 'setuptools>=68.0.0' 'wheel>=0.41.1' 'build>=1'
cross-pip install -U 'pip>=23.2.1' 'setuptools>=68.0.0' 'wheel>=0.41.1' 'build>=1'
build-pip install cffi
cross-expose cffi
cross-pip install -e ../../
cross-pip list

export DIST_EXTRA_CONFIG=/tmp/build-opts.cfg
echo -e "[bdist_wheel]\npy_limited_api=cp37" > $DIST_EXTRA_CONFIG

rm -rf dist/*
cross-python -m build --no-isolation
ls -la dist/
python -m zipfile -l dist/*.whl # debug all files inside wheel file
    """

    pwd = os.getcwd()
    session.run(
        "docker",
        "run",
        "--rm",
        "-v",
        f"{pwd}:/io",
        "-w",
        "/io",
        f"messense/manylinux2014-cross:{arch}",
        "bash",
        "-c",
        script_build,
        external=True,
    )

    script_check = """set -ex
cd /io/examples
python3 --version
pip3 install rust_with_cffi/dist/rust_with_cffi*.whl
python3 -c "from rust_with_cffi import rust; assert rust.rust_func() == 14"
python3 -c "from rust_with_cffi.cffi import lib; assert lib.cffi_func() == 15"
"""

    session.run(
        "docker",
        "run",
        "--rm",
        "-v",
        f"{pwd}:/io",
        "-w",
        "/io",
        "--platform",
        docker_platform,
        "python:3.11",
        "bash",
        "-c",
        script_check,
        external=True,
    )


@nox.session()
def ruff(session: nox.Session):
    session.install("ruff")
    session.run("ruff", "format", "--check", ".")
    session.run("ruff", ".")


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

        session.install("pytest", "cffi<1.16")
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


@nox.session()
def docs(session: nox.Session):
    session.install(".", "-r", "docs/requirements.txt")
    session.run("python", "-m", "sphinx", "docs", "docs/_build", *session.posargs)
