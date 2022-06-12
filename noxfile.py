import os
import re
import sys
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
    session.run("pytest", "setuptools_rust", *session.posargs)


class EmscriptenInfo:
    def __init__(self):
        rootdir = Path(__file__).parent
        self.emscripten_dir = rootdir / "emscripten"
        self.builddir = rootdir / ".nox/emscripten"
        self.builddir.mkdir(exist_ok=True, parents=True)

        self.pyversion = sys.version.split()[0]
        self.pymajor, self.pyminor, self.pymicro = self.pyversion.split(".")
        self.pymicro, self.pydev = re.match(
            "([0-9]*)([^0-9].*)?", self.pymicro
        ).groups()
        if self.pydev is None:
            self.pydev = ""

        self.pymajorminor = f"{self.pymajor}.{self.pyminor}"
        self.pymajorminormicro = f"{self.pymajorminor}.{self.pymicro}"
        self.emscripten_version = "3.1.13"

        underscore_emscripten_version = self.emscripten_version.replace(".", "_")
        cp = f"cp{self.pymajor}{self.pyminor}"
        self.wheel_suffix = (
            f"{cp}-{cp}-emscripten_{underscore_emscripten_version}_wasm32.whl"
        )

    def build(self, session, target):
        session.run(
            "make",
            "-C",
            str(self.emscripten_dir),
            target,
            f"BUILDROOT={self.builddir}",
            f"PYMAJORMINORMICRO={self.pymajorminormicro}",
            f"PYPRERELEASE={self.pydev}",
            f"EMSCRIPTEN_VERSION={self.emscripten_version}",
            external=True,
        )


@nox.session(name="build-emscripten-libpython", venv_backend="none")
def build_emscripten_libpython(session: nox.Session):
    info = EmscriptenInfo()
    info.build(session, "libpython")


@nox.session(name="build-emscripten-namespace-package-wheel")
def build_emscripten_namespace_package_wheel(session: nox.Session):
    session.install(".")
    info = EmscriptenInfo()
    session.run(
        "rustup",
        "target",
        "add",
        "wasm32-unknown-emscripten",
        "--toolchain",
        "nightly",
        external=True,
    )
    session.run(
        "rustup",
        "component",
        "add",
        "rust-src",
        "--toolchain",
        "nightly",
        external=True,
    )
    info.build(session, "namespace_package_wheel")


@nox.session(name="build-emscripten-interpreter", venv_backend="none")
def build_emscripten_interpreter(session: nox.Session):
    info = EmscriptenInfo()
    info.build(session, "python-interpreter")


@nox.session(name="test-emscripten-namespace-package-wheel")
def test_emscripten_namespace_package_wheel(session: nox.Session):
    session.install("wheel")

    info = EmscriptenInfo()
    dist_dir = Path("examples/namespace_package/dist/").resolve()
    pkg = "namespace_package-0.1.0"
    with session.chdir(dist_dir):
        session.run(
            "wheel",
            "unpack",
            f"{pkg}-{info.wheel_suffix}",
            external=True,
        )

    with session.chdir("emscripten/interpreter"):
        session.run(
            "node",
            "--experimental-wasm-bigint",
            "main.js",
            str(dist_dir / pkg),
            external=True,
        )
