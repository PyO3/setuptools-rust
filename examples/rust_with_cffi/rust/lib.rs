use pyo3::prelude::*;

#[pymodule]
mod rust {
    use pyo3::prelude::*;

    #[pyfunction]
    fn rust_func() -> PyResult<u64> {
        return Ok(14);
    }
}
