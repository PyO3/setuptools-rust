#!/usr/bin/env python
from glob import glob
import os

import html_py_ever
import pytest
from bs4 import BeautifulSoup
from html_py_ever import Document


HTML_FILES = glob(os.path.join(os.path.dirname(__file__), "*.html"))


def rust(filename: str) -> Document:
    return html_py_ever.parse_file(filename)


def python(filename: str) -> BeautifulSoup:
    with open(filename, encoding="utf8") as fp:
        soup = BeautifulSoup(fp, "html.parser")

    return soup


@pytest.mark.parametrize("filename", HTML_FILES)
def test_bench_parsing_rust(benchmark, filename):
    benchmark(rust, filename)


@pytest.mark.parametrize("filename", HTML_FILES)
def test_bench_parsing_python(benchmark, filename):
    benchmark(python, filename)
