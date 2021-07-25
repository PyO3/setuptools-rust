import cffi


ffi = cffi.FFI()
ffi.cdef(
    """
int cffi_func(void);
"""
)
ffi.set_source(
    "rust_with_cffi.cffi",
    """
int cffi_func(void) {
	return 15;
}
""",
)
