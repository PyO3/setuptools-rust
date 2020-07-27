#[macro_use]
extern crate pyo3;

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

#[pyfunction]
fn hello(_py: Python) -> PyResult<()> {
    println!("Hello, world!");
    Ok(())
}


#[pymodule]
/// Module documentation string
fn english(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(hello))?;
    Ok(())
}
