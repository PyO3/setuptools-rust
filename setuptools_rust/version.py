__version__ = version = "1.13.0"
__version_tuple__ = version_tuple = tuple(
    int(x[1]) if x[0] < 3 else x[1] for x in enumerate(__version__.split("."))
)
