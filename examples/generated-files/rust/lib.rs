#[pyo3::pymodule]
mod _lib {
    use pyo3::prelude::*;

    #[pyfunction]
    fn library_ok() -> bool {
        true
    }
}
