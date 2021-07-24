from rust_with_cffi import rust
from rust_with_cffi.cffi import lib


def test_rust():
    assert rust.rust_func() == 14


def test_cffi():
    assert lib.cffi_func() == 15
