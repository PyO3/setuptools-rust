use pyo3::prelude::*;
use std::env;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

/// Calls Python (see https://pyo3.rs for details)
#[pyfunction]
fn demo(py: Python) -> PyResult<()> {
    let argv = env::args().collect::<Vec<_>>();
    println!("argv = {:?}", argv);
    // argv[0]: Python path, argv[1]: program name, argv[2..]: given args

    let numbers: Vec<i32> = argv[2..].iter().map(|s| s.parse().unwrap()).collect();

    let python_sum = PyModule::import(py, "builtins")?.getattr("sum")?;
    let total: i32 = python_sum.call1((numbers,))?.extract()?;
    println!("sum({}) = {:?}", argv[2..].join(", "), total);
    Ok(())
}

/// A Python module implemented in Rust. The name of this function must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
#[pymodule]
fn _lib(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(demo, m)?)?;
    Ok(())
}
