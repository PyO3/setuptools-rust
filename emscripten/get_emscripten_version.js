import { loadPyodide } from "pyodide";

const pyodide = await loadPyodide();

pyodide.runPython(`
import platform
print(platform.platform().split("-")[1])
`);
