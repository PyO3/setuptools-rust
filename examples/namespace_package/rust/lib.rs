use pyo3::prelude::*;

/// A Python module implemented in Rust.
#[pymodule]
mod rust {
    use pyo3::prelude::*;

    #[pyfunction]
    fn rust_func() -> usize {
        14
    }
}
