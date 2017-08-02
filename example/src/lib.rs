#![feature(proc_macro)]

extern crate pyo3;

use pyo3::*;

/// Module documentation string
#[py::modinit(_helloworld)]
fn init(py: Python, m: &PyModule) -> PyResult<()> {

    #[pyfn(m, "run", args="*", kwargs="**")]
    fn run_fn(py: Python, args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<()> {
        run(py, args, kwargs)
    }

    #[pyfn(m, "val")]
    fn val(_py: Python) -> PyResult<i32> {
        Ok(42)
    }

    Ok(())
}

fn run(py: Python, args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<()> {
    println!("Rust says: Hello Python!");
    for arg in args.iter() {
        println!("Rust got {}", arg.as_ref(py));
    }
    if let Some(kwargs) = kwargs {
        for (key, val) in kwargs.items_vec() {
            println!("{} = {}", key.as_ref(py), val.as_ref(py));
        }
    }
    Ok(())
}
