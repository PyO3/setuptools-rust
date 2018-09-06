#!/usr/bin/env python3
from glob import glob
from time import perf_counter
from typing import Tuple

import html_py_ever
from bs4 import BeautifulSoup


def rust(filename: str) -> Tuple[int, float, float]:
    start_load = perf_counter()
    doc = html_py_ever.parse_file(filename)
    end_load = perf_counter()

    start_search = perf_counter()
    links = doc.select("a[href]")
    end_search = perf_counter()

    return len(links), end_load - start_load, end_search - start_search


def python(filename: str) -> Tuple[int, float, float]:
    start_load = perf_counter()
    with open(filename) as fp:
        text = fp.read()
    soup = BeautifulSoup(text, "html.parser")

    end_load = perf_counter()
    start_search = perf_counter()

    links = soup.select("a[href]")
    end_search = perf_counter()

    return len(links), end_load - start_load, end_search - start_search


def main():
    for filename in glob("*.html"):
        count_rs, parse_rs, select_rs = rust(filename)
        count_py, parse_py, select_py = python(filename)
        assert count_rs == count_py
        print(f"{filename} {count_rs}")
        print(f"Parse  {parse_rs:6f}s {parse_py:6f}s {parse_py/parse_rs:6.3f}x")
        print(f"Select {select_py:6f}s {select_rs:6f}s {select_py/select_rs:6.3f}x")


if __name__ == "__main__":
    main()
