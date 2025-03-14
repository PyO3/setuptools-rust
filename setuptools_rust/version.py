__version__ = version = "1.11.0"
__version_tuple__ = version_tuple = tuple(
    map(lambda x: int(x[1]) if x[0] < 3 else x[1], enumerate(__version__.split(".")))
)
