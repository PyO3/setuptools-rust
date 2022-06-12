import sys
sys.path.append("/package_dir")

from namespace_package import python
print("python.python_func()", python.python_func())
assert python.python_func() == 15

from namespace_package import rust
print("rust.rust_func()", rust.rust_func())
assert rust.rust_func() == 14
