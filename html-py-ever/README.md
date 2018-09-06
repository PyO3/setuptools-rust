# html-py-ever

Using [html5ever](https://github.com/servo/html5ever) through [kuchiki](https://github.com/kuchiki-rs/kuchiki) to speed up html parsing and css-selecting.

## Benchmarking

Create a python 3.6+ venv and activate it. Install html-py-ever in there (`python setup.py install`). To get a readable benchmark, run `test/run_all.py`. To get a real benchmark, run `pytest test_parsing.py` or `pytest test_selector.py`. Both have a `--benchmark-histogram` option.
