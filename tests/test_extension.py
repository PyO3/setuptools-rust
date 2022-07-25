from pathlib import Path

import pytest
from pytest import CaptureFixture, MonkeyPatch

from setuptools_rust.extension import RustBin


@pytest.fixture()
def hello_world_bin() -> RustBin:
    setuptools_rust_dir = Path(__file__).parent.parent
    return RustBin(
        "hello-world",
        path=(
            setuptools_rust_dir / "examples" / "hello-world" / "Cargo.toml"
        ).as_posix(),
    )


def test_metadata_contents(hello_world_bin: RustBin) -> None:
    metadata = hello_world_bin.metadata(quiet=False)
    assert "target_directory" in metadata


def test_metadata_cargo_log(
    capfd: CaptureFixture, monkeypatch: MonkeyPatch, hello_world_bin: RustBin
) -> None:
    monkeypatch.setenv("CARGO_LOG", "trace")

    # With quiet unset, no stdout, plenty of logging stderr
    hello_world_bin.metadata(quiet=False)
    captured = capfd.readouterr()
    assert captured.out == ""
    assert "TRACE cargo::util::config" in captured.err

    # With quiet set, nothing will be printed
    hello_world_bin.metadata(quiet=True)
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""
