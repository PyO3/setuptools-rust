#![feature(proc_macro)]

extern crate pyo3;

use pyo3::prelude::*;

/// Module documentation string
#[py::modinit(english)]
fn init(py: Python, m: &PyModule) -> PyResult<()> {

    #[pyfn(m, "hello")]
    fn hello(_py: Python) -> PyResult<()> {
        println!("Hello, world!");
        Ok(())
    }

    Ok(())
}
