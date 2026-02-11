import os
import shutil
import sys
import tempfile
from contextlib import ExitStack
from glob import glob
from inspect import cleandoc as heredoc
from pathlib import Path

import nox
import nox.command


@nox.session(name="test-examples", venv_backend="none")
def test_examples(session: nox.Session):
    for example in glob("examples/*/noxfile.py"):
        session.run("nox", "-f", example, external=True)


@nox.session(name="test-sdist-vendor")
def test_sdist_vendor(session: nox.Session):
    session.install(".", "build")
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
python3.13 -m pip install crossenv
python3.13 -m crossenv "/opt/python/cp313-cp313/bin/python3" --cc $TARGET_CC --cxx $TARGET_CXX --sysroot $TARGET_SYSROOT --env LIBRARY_PATH= --manylinux manylinux1 /venv
. /venv/bin/activate

build-pip install -U 'pip>=23.2.1' 'setuptools>=70.1' 'build>=1'
cross-pip install -U 'pip>=23.2.1' 'setuptools>=70.1' 'build>=1'
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
        "python:3.13",
        "bash",
        "-c",
        script_check,
        external=True,
    )


@nox.session(name="test-cross")
def test_cross(session: nox.Session):
    session.install(".")
    session.install("-U", "setuptools", "build")

    shutil.rmtree("examples/namespace_package/dist", ignore_errors=True)

    namespace_package = Path(__file__).parent / "examples" / "namespace_package"
    os.chdir(namespace_package)
    session.run(
        "docker",
        "build",
        "-t",
        "cross-pyo3:aarch64-unknown-linux-gnu",
        ".",
        external=True,
    )

    major_version = sys.version_info[0]
    minor_version = sys.version_info[1]

    cpXY = f"cp{major_version}{minor_version}"

    tmp = Path(session.create_tmp())
    extra_config = tmp / "build-opts.cfg"
    build_config = """
        [bdist_wheel]
        plat_name = manylinux2014_aarch64
        """
    extra_config.write_text(heredoc(build_config), encoding="utf-8")

    build_env = os.environ.copy()
    build_env["DIST_EXTRA_CONFIG"] = str(extra_config.absolute())
    build_env["CARGO"] = "cross"
    build_env["CARGO_BUILD_TARGET"] = "aarch64-unknown-linux-gnu"
    build_env["PYO3_CROSS_LIB_DIR"] = f"/opt/python/{cpXY}-{cpXY}/lib"

    # build wheel using cross
    #
    # if this step fails, you may need to install cross:
    # cargo install cross --git https://github.com/cross-rs/cross
    session.run("python", "-m", "build", "--no-isolation", env=build_env)

    script_check = """
set -eux
python3 --version
python3 -m venv .venv
source .venv/bin/activate
pip install namespace_package --no-index --find-links /io/dist/ --force-reinstall
python -c "from namespace_package import rust; assert rust.rust_func() == 14"
python -c "from namespace_package import python; assert python.python_func() == 15"
"""

    session.run(
        "docker",
        "run",
        "--rm",
        "-v",
        f"{namespace_package}:/io",
        "-w",
        "/io",
        "--platform",
        "aarch64",
        f"python:3.{minor_version}",
        "bash",
        "-c",
        script_check,
        external=True,
    )


@nox.session()
def ruff(session: nox.Session):
    session.install("ruff")
    session.run("ruff", "format", "--diff", ".")
    session.run("ruff", "check", ".")


@nox.session()
def mypy(session: nox.Session):
    session.install("mypy", "fat_macho", "types-setuptools", ".")
    session.run("mypy", "setuptools_rust", *session.posargs)


@nox.session()
def test(session: nox.Session):
    session.install("pytest", ".")
    session.run("pytest", "setuptools_rust", "tests", *session.posargs)


PYODIDE_VERSION = "0.29.1"
EMSCRIPTEN_DIR = Path("./emscripten").resolve()


@nox.session(name="install-pyodide-emscripten")
def install_pyodide_emscripten(session: nox.Session):
    with session.chdir(EMSCRIPTEN_DIR):
        session.run("npm", "install", f"pyodide@{PYODIDE_VERSION}", external=True)
        emscripten_version = session.run(
            "node", "get_emscripten_version.js", external=True, silent=True
        ).strip()
        python_version = session.run(
            "node", "get_python_version.js", external=True, silent=True
        ).strip()

    with ExitStack() as stack:
        if "GITHUB_ENV" in os.environ:
            out = stack.enter_context(open(os.environ["GITHUB_ENV"], "a"))
        else:
            out = sys.stdout

        print(f"PYODIDE_VERSION={PYODIDE_VERSION}", file=out)
        print(f"EMSCRIPTEN_VERSION={emscripten_version}", file=out)
        print(f"PYTHON_VERSION={python_version}", file=out)

        if "GITHUB_ENV" not in os.environ:
            print(
                "You will need to install emscripten yourself to match the target version."
            )


@nox.session(name="test-examples-emscripten")
def test_examples_emscripten(session: nox.Session):
    session.install(".", "build")

    examples_dir = Path("examples").absolute()
    test_crates = [
        examples_dir / "html-py-ever",
        examples_dir / "namespace_package",
    ]

    python_version = os.environ["PYTHON_VERSION"]
    emscripten_version = os.environ["EMSCRIPTEN_VERSION"]

    with tempfile.NamedTemporaryFile("w") as pyo3_config:
        pyo3_config.write(f"""\
implementation=CPython
version={python_version}
shared=true
abi3=false
pointer_width=32
""")
        pyo3_config.flush()

        emscripten_version_joined = emscripten_version.replace(".", "_")

        for example in test_crates:
            env = os.environ.copy()
            env.update(
                PYTHONPATH=str(EMSCRIPTEN_DIR),
                _PYTHON_SYSCONFIGDATA_NAME="_sysconfigdata__emscripten_wasm32-emscripten",
                _PYTHON_HOST_PLATFORM=f"emscripten_{emscripten_version_joined}_wasm32",
                CARGO_BUILD_TARGET="wasm32-unknown-emscripten",
                CARGO_TARGET_WASM32_UNKNOWN_EMSCRIPTEN_LINKER=str(
                    EMSCRIPTEN_DIR / "emcc_wrapper.py"
                ),
                PYO3_CONFIG_FILE=pyo3_config.name,
            )
            with session.chdir(example):
                cmd = ["python", "-m", "build", "--wheel", "--no-isolation"]
                session.run(*cmd, env=env, external=True)

            with session.chdir(EMSCRIPTEN_DIR):
                session.run("node", "runner.js", str(example), external=True)


@nox.session(name="bump-version")
def bump_version(session: nox.Session) -> None:
    session.install("bump2version")
    session.run("bumpversion", *session.posargs)


@nox.session()
def docs(session: nox.Session):
    session.install(".", "-r", "docs/requirements.txt")
    session.run("python", "-m", "sphinx", "docs", "docs/_build", *session.posargs)
