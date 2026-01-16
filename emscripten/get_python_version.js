import { loadPyodide } from "pyodide";

const pyodide = await loadPyodide();

pyodide.runPython(`
import sys
major, minor = sys.version_info[:2]
print(f"{major}.{minor}")
`);
