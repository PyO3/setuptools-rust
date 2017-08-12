#![feature(proc_macro)]

extern crate pyo3;

use pyo3::prelude::*;

/// Module documentation string
#[py::modinit(_helloworld)]
fn init(py: Python, m: &PyModule) -> PyResult<()> {

    #[pyfn(m, "run", args="*", kwargs="**")]
    fn run_fn(_py: Python, args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<()> {
        run(args, kwargs)
    }

    #[pyfn(m, "val")]
    fn val(_py: Python) -> PyResult<i32> {
        Ok(42)
    }

    Ok(())
}

fn run(args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<()> {
    println!("Rust says: Hello Python!");
    for arg in args.iter() {
        println!("Rust got {}", arg);
    }
    if let Some(kwargs) = kwargs {
        for (key, val) in kwargs.iter() {
            println!("{} = {}", key, val);
        }
    }
    Ok(())
}
