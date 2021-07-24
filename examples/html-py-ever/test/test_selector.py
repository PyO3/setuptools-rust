#!/usr/bin/env python
from glob import glob
import os

import html_py_ever
import pytest
from bs4 import BeautifulSoup


HTML_FILES = glob(os.path.join(os.path.dirname(__file__), "*.html"))


@pytest.mark.parametrize("filename", HTML_FILES)
def test_bench_selector_rust(benchmark, filename):
    document = html_py_ever.parse_file(filename)
    benchmark(document.select, "a[href]")


@pytest.mark.parametrize("filename", HTML_FILES)
def test_bench_selector_python(benchmark, filename):
    with open(filename, encoding="utf8") as fp:
        soup = BeautifulSoup(fp, "html.parser")
    benchmark(soup.select, "a[href]")
