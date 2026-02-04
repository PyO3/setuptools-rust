use pyo3::prelude::*;

#[pymodule]
mod html_py_ever {
    use pyo3::prelude::*;
    use scraper::{Html, Selector};
    use std::fs;
    use std::io::Read;
    use std::path::Path;

    /// A parsed html document
    #[pyclass(unsendable)]
    struct Document {
        html: Html,
    }

    #[pymethods]
    impl Document {
        /// Returns the selected elements as strings
        fn select(&self, selector: &str) -> PyResult<Vec<String>> {
            let selector = Selector::parse(selector)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("{e:?}")))?;
            Ok(self
                .html
                .select(&selector)
                .map(|element| element.html())
                .collect())
        }
    }

    impl Document {
        fn from_reader(reader: &mut impl Read) -> PyResult<Document> {
            let mut html_string = String::new();
            reader.read_to_string(&mut html_string)?;
            let html = Html::parse_document(&html_string);
            Ok(Document { html })
        }

        fn from_file(path: &Path) -> PyResult<Document> {
            let html_string = fs::read_to_string(path)?;
            let html = Html::parse_document(&html_string);
            Ok(Document { html })
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
}
