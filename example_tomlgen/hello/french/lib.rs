#![feature(proc_macro)]

extern crate pyo3;

use pyo3::prelude::*;
use pyo3::py::modinit;

/// Module documentation string
#[modinit("french")]
fn init(py: Python, m: &PyModule) -> PyResult<()> {

    #[pyfn(m, "hello")]
    fn hello(_py: Python) -> PyResult<()> {
        println!("Bonjour, monde!");
        Ok(())
    }

    Ok(())
}
