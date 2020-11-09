use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::io::Read;
use std::path::Path;
use tendril::stream::TendrilSink;

/// A parsed html document
#[pyclass(unsendable)]
struct Document {
    node: kuchiki::NodeRef,
}

#[pymethods]
impl Document {
    /// Returns the selected elements as strings
    fn select(&self, selector: &str) -> Vec<String> {
        self.node
            .select(selector)
            .unwrap()
            .map(|css_match| css_match.text_contents())
            .collect()
    }
}

impl Document {
    fn from_reader(reader: &mut impl Read) -> PyResult<Document> {
        let node = kuchiki::parse_html().from_utf8().read_from(reader)?;
        Ok(Document { node })
    }

    fn from_file(path: &Path) -> PyResult<Document> {
        let node = kuchiki::parse_html().from_utf8().from_file(path)?;
        Ok(Document { node })
    }
}

/// Parses the File from the specified Path into a document
#[pyfunction]
fn parse_file(path: &str) -> PyResult<Document> {
    let document = Document::from_file(Path::new(path))?;
    Ok(document)
}

/// Parses the given html test into a document
#[pyfunction]
fn parse_text(text: &str) -> PyResult<Document> {
    let document = Document::from_reader(&mut text.as_bytes())?;
    Ok(document)
}

#[pymodule]
fn html_py_ever(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(parse_file))?;
    m.add_wrapped(wrap_pyfunction!(parse_text))?;
    m.add_class::<Document>()?;

    Ok(())
}
