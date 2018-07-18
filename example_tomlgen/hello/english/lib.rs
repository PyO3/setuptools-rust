#![feature(use_extern_macros)]

extern crate pyo3;

use pyo3::prelude::*;

/// Module documentation string
#[pymodinit]
fn english(py: Python, m: &PyModule) -> PyResult<()> {

    #[pyfn(m, "hello")]
    fn hello(_py: Python) -> PyResult<()> {
        println!("Hello, world!");
        Ok(())
    }

    Ok(())
}
