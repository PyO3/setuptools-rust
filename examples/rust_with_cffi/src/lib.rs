use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

#[pyfunction]
fn rust_func() -> PyResult<u64> {
	return Ok(14);
}

#[pymodule]
fn rust(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(rust_func))?;

    Ok(())
}