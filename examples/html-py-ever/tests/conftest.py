import sys
import pytest

if sys.platform == "emscripten":

    @pytest.fixture
    def benchmark():
        def result(func, *args, **kwargs):
            return func(*args, **kwargs)

        return result
