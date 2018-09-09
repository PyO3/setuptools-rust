#!/usr/bin/env python
from glob import glob

import html_py_ever
import pytest
from bs4 import BeautifulSoup
from html_py_ever import Document


def rust(filename: str) -> Document:
    return html_py_ever.parse_file(filename)


def python(filename: str) -> BeautifulSoup:
    with open(filename) as fp:
        soup = BeautifulSoup(fp, "html.parser")

    return soup


@pytest.mark.parametrize("filename", list(glob("*.html")))
def test_bench_parsing_rust(benchmark, filename):
    benchmark(rust, filename)


@pytest.mark.parametrize("filename", list(glob("*.html")))
def test_bench_parsing_python(benchmark, filename):
    benchmark(python, filename)
