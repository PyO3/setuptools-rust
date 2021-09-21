# html-py-ever

Demoing how to use [html5ever](https://github.com/servo/html5ever) through [kuchiki](https://github.com/kuchiki-rs/kuchiki) to speed up html parsing and css-selecting.

## Usage

`parse_file` and `parse_text` return a parsed `Document`, which then lets you select elements by css selectors using the `select` method. All elements are returned as strings

## Benchmarking

Run `tox -e py`.

## Example benchmark results

Running on Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz with Python 3.9.5 and Rust 1.55.0

**run_all.py**

```
$ ./test/run_all.py
/home/david/dev/setuptools-rust/examples/html-py-ever/test/empty.html 0 0.000026s
Parse py    0.000070s  2.693x
Select py   0.000105s 12.221x
Parse lxml  0.000209s  8.023x
Select lxml 0.000151s 17.535x
/home/david/dev/setuptools-rust/examples/html-py-ever/test/small.html 0 0.000032s
Parse py    0.000286s  9.066x
Select py   0.000080s  3.038x
Parse lxml  0.000396s 12.525x
Select lxml 0.000087s  3.264x
/home/david/dev/setuptools-rust/examples/html-py-ever/test/rust.html 733 0.015430s
Parse py    0.257859s 16.711x
Select py   0.024799s 32.135x
Parse lxml  0.166995s 10.822x
Select lxml 0.024668s 31.966x
/home/david/dev/setuptools-rust/examples/html-py-ever/test/python.html 1518 0.065441s
Parse py    1.371898s 20.964x
Select py   0.138580s 43.215x
Parse lxml  0.917728s 14.024x
Select lxml 0.146618s 45.721x
/home/david/dev/setuptools-rust/examples/html-py-ever/test/monty-python.html 1400 0.007463s
Parse py    0.184073s 24.664x
Select py   0.015596s 29.757x
Parse lxml  0.076753s 10.284x
Select lxml 0.017100s 32.628x
```

**test_parsing.py**

```
------------------------------------------------------------------------------------------------------------------------------------------------ benchmark: 10 tests -------------------------------------------------------------------------------------------------------------------------------------------------
Name (time in us)                                                                                                      Min                       Max                      Mean
StdDev                    Median                    IQR            Outliers           OPS            Rounds  Iterations
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_bench_parsing_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/empty.html]                      2.1000 (1.0)            155.2000 (1.0)              2.7308 (1.0)
2.0262 (1.0)              2.4000 (1.0)           0.1000 (1.0)      341;2539  366,186.4074 (1.0)       18762           1
test_bench_parsing_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/small.html]                      9.6000 (4.57)           559.3000 (3.60)            10.4213 (3.82)
4.6027 (2.27)            10.2000 (4.25)          0.3000 (3.00)      294;850   95,957.4914 (0.26)      24571           1
test_bench_parsing_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/empty.html]                   24.1000 (11.48)          525.8000 (3.39)            30.5076 (11.17)        13.4886 (6.66)            26.6000 (11.08)         1.7000 (17.00)    919;1597   32,778.7273 (0.09)      10236           1
test_bench_parsing_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/small.html]                  187.2000 (89.14)          582.8000 (3.76)           215.0146 (78.74)        35.1708 (17.36)          200.6000 (83.58)        21.8000 (218.00)    340;336    4,650.8477 (0.01)       3158           1
test_bench_parsing_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/monty-python.html]           6,668.5000 (>1000.0)     16,104.0000 (103.76)       7,878.4104 (>1000.0)   1,223.6380 (603.90)       7,504.4000 (>1000.0)     776.1000 (>1000.0)      10;9      126.9292 (0.00)        134           1
test_bench_parsing_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/rust.html]                  14,551.0000 (>1000.0)     16,078.2000 (103.60)      15,117.5525 (>1000.0)     237.0122 (116.97)      15,072.3000 (>1000.0)     155.1500 (>1000.0)     11;10       66.1483 (0.00)         61           1
test_bench_parsing_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/python.html]                69,374.7000 (>1000.0)     88,828.3000 (572.35)      73,736.0067 (>1000.0)   6,102.6659 (>1000.0)     71,318.8000 (>1000.0)   3,288.9000 (>1000.0)       2;3       13.5619 (0.00)         15           1
test_bench_parsing_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/monty-python.html]       119,087.1000 (>1000.0)    140,231.5000 (903.55)     124,006.4333 (>1000.0)   8,041.2631 (>1000.0)    120,803.8000 (>1000.0)   2,573.4000 (>1000.0)       1;1        8.0641 (0.00)          6           1
test_bench_parsing_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/rust.html]               256,079.1000 (>1000.0)    283,591.4000 (>1000.0)    272,005.6800 (>1000.0)  11,993.9084 (>1000.0)    276,622.5000 (>1000.0)  20,551.0250 (>1000.0)       1;0        3.6764 (0.00)          5           1
test_bench_parsing_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/python.html]           1,388,658.5000 (>1000.0)  1,417,244.1000 (>1000.0)  1,407,207.0600 (>1000.0)  11,658.8211 (>1000.0)  1,407,273.7000 (>1000.0)  15,582.4000 (>1000.0)       1;0        0.7106 (0.00)          5           1
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```

**test_selector.py**

```
-------------------------------------------------------------------------------------------------------------------------------------------------------- benchmark: 10 tests --------------------------------------------------------------------------------------------------------------------------------------------------------
Name (time in ns)                                                                                                         Min                         Max                        Mean
          StdDev                      Median                       IQR            Outliers           OPS            Rounds  Iterations
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_bench_selector_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/empty.html]                      799.9997 (1.0)          682,700.0007 (11.08)          1,079.2724 (1.0)          5,056.3097 (6.85)             999.9994 (1.0)             99.9999 (>1000.0)    87;499  926,550.1666 (1.0)       53764           1
test_bench_selector_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/small.html]                      899.9996 (1.12)         102,799.9997 (1.67)           1,134.4583 (1.05)           738.3883 (1.0)            1,100.0002 (1.10)             0.0009 (1.0)     664;51478  881,477.9722 (0.95)     158731           1
test_bench_selector_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/empty.html]                  7,000.0006 (8.75)          61,600.0007 (1.0)            7,896.1815 (7.32)         2,197.4336 (2.98)           7,600.0006 (7.60)           300.0005 (>1000.0)   159;411  126,643.4926 (0.14)       9192           1
test_bench_selector_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/small.html]                 24,600.0000 (30.75)      1,270,499.9999 (20.62)         26,831.8769 (24.86)       10,644.6522 (14.42)         26,300.0002 (26.30)          599.9991 (>1000.0)   237;871   37,269.1035 (0.04)      15083           1
test_bench_selector_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/monty-python.html]           288,299.9997 (360.38)     1,328,100.0001 (21.56)        330,258.3420 (306.00)      36,035.7334 (48.80)        323,899.9998 (323.90)       9,299.9999 (>1000.0)   148;273    3,027.9326 (0.00)       1930           1
test_bench_selector_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/rust.html]                   323,400.0005 (404.25)     2,079,099.9997 (33.75)        361,308.3042 (334.77)      61,858.2904 (83.77)        354,000.0002 (354.00)      16,300.0004 (>1000.0)    39;115    2,767.7194 (0.00)       1144           1
test_bench_selector_rust[/home/david/dev/setuptools-rust/examples/html-py-ever/test/python.html]               2,952,400.0001 (>1000.0)    4,020,800.0000 (65.27)      3,093,027.3333 (>1000.0)    117,355.5598 (158.93)     3,067,149.9999 (>1000.0)     82,000.0000 (>1000.0)     26;18      323.3078 (0.00)        300           1
test_bench_selector_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/monty-python.html]      14,984,299.9999 (>1000.0)   16,412,400.0003 (266.44)    15,363,483.8710 (>1000.0)    385,910.8544 (522.64)    15,212,300.0003 (>1000.0)    228,699.9988 (>1000.0)       9;9       65.0894 (0.00)         62           1
test_bench_selector_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/rust.html]              22,151,300.0006 (>1000.0)   27,046,000.0002 (439.06)    24,152,934.1463 (>1000.0)  1,014,946.2212 (>1000.0)   23,943,899.9997 (>1000.0)    420,224.9995 (>1000.0)      9;10       41.4028 (0.00)         41           1
test_bench_selector_python[/home/david/dev/setuptools-rust/examples/html-py-ever/test/python.html]           139,399,100.0004 (>1000.0)  148,564,900.0006 (>1000.0)  143,540,675.0002 (>1000.0)  3,466,075.6279 (>1000.0)  143,609,199.9999 (>1000.0)  6,241,799.9993 (>1000.0)       4;0        6.9667 (0.00)          8           1
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```

## build instructions

**Requirements:**

-   rust-toolchain (i.e cargo, rustc)
-   python3-dev or python3-devel

**building and installing**
```
pip install setuptools-rust setuptools wheel
python3 setup.py install --user
```

github workflows example to test and upload the module to pypi [here](./.github/workflows/upload.yml)
