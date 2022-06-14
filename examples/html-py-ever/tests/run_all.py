#!/usr/bin/env python3
import os
from glob import glob
from time import perf_counter
from typing import Tuple

import html_py_ever
from bs4 import BeautifulSoup

try:
    import lxml

    HAVE_LXML = True
except ImportError:
    HAVE_LXML = False


def rust(filename: str) -> Tuple[int, float, float]:
    start_load = perf_counter()
    doc = html_py_ever.parse_file(filename)
    end_load = perf_counter()

    start_search = perf_counter()
    links = doc.select("a[href]")
    end_search = perf_counter()

    return len(links), end_load - start_load, end_search - start_search


def python(filename: str, parser: str) -> Tuple[int, float, float]:
    start_load = perf_counter()
    with open(filename, encoding="utf8") as fp:
        soup = BeautifulSoup(fp, parser)

    end_load = perf_counter()
    start_search = perf_counter()

    links = soup.select("a[href]")
    end_search = perf_counter()

    return len(links), end_load - start_load, end_search - start_search


def main():
    files_glob = os.path.abspath(os.path.join(os.path.dirname(__file__), "*.html"))
    for filename in glob(files_glob):
        count_rs, parse_rs, select_rs = rust(filename)
        count_py, parse_py, select_py = python(filename, "html.parser")
        assert count_rs == count_py
        print(f"{filename} {count_rs} {parse_rs:6f}s")
        print(f"Parse py    {parse_py:6f}s {parse_py/parse_rs:6.3f}x")
        print(f"Select py   {select_py:6f}s {select_py/select_rs:6.3f}x")

        if HAVE_LXML:
            count_lxml, parse_lxml, select_lxml = python(filename, "lxml")
            assert count_rs == count_lxml
            print(f"Parse lxml  {parse_lxml:6f}s {parse_lxml/parse_rs:6.3f}x")
            print(f"Select lxml {select_lxml:6f}s {select_lxml/select_rs:6.3f}x")


if __name__ == "__main__":
    main()
