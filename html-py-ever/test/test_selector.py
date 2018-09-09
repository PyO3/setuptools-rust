#!/usr/bin/env python
from glob import glob

import html_py_ever
import pytest
from bs4 import BeautifulSoup


@pytest.mark.parametrize("filename", list(glob("*.html")))
def test_bench_selector_rust(benchmark, filename):
    document = html_py_ever.parse_file(filename)
    benchmark(document.select, "a[href]")


@pytest.mark.parametrize("filename", list(glob("*.html")))
def test_bench_selector_python(benchmark, filename):
    with open(filename) as fp:
        soup = BeautifulSoup(fp, "html.parser")
    benchmark(soup.select, "a[href]")
