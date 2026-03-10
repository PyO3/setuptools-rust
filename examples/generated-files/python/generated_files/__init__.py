__all__ = ["library_ok", "data_files_content"]

from pathlib import Path
from ._lib import library_ok


def data_files_content() -> dict[Path, str]:
    us = Path(__file__).parent
    paths = [us / "my_file.txt"]
    paths.extend((us / "_data" / "dir").glob("*.txt"))
    return {path.relative_to(us): path.read_text() for path in paths}
