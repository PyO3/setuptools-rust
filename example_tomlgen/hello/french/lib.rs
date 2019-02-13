#[macro_use]
extern crate pyo3;

use pyo3::prelude::*;

#[pyfunction]
fn hello(_py: Python) -> PyResult<()> {
    println!("Bonjour, monde!");
    Ok(())
}


#[pymodule]
/// Module documentation string
fn french(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(hello))?;
    Ok(())
}
