from namespace_package import rust, python


def test_rust():
    assert rust.rust_func() == 14


def test_cffi():
    assert python.python_func() == 15
