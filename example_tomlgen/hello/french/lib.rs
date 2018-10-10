extern crate pyo3;

use pyo3::prelude::*;

/// Module documentation string
#[pymodinit]
fn french(_py: Python, m: &PyModule) -> PyResult<()> {

    #[pyfn(m, "hello")]
    fn hello(_py: Python) -> PyResult<()> {
        println!("Bonjour, monde!");
        Ok(())
    }

    Ok(())
}
