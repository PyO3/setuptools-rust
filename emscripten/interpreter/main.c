#define PY_SSIZE_T_CLEAN
#include "Python.h"
#include <assert.h>
#include <emscripten.h>


#define FAIL_IF_STATUS_EXCEPTION(status)                                       \
  if (PyStatus_Exception(status)) {                                            \
    goto finally;                                                              \
  }


// Initialize python. exit() and print message to stderr on failure.
static void
initialize_python()
{
  int success = 0;
  PyStatus status;
  PyConfig config;
  PyConfig_InitPythonConfig(&config);
  status = PyConfig_SetBytesString(&config, &config.home, "/");
  FAIL_IF_STATUS_EXCEPTION(status);
  config.write_bytecode = 0;
  status = Py_InitializeFromConfig(&config);
  FAIL_IF_STATUS_EXCEPTION(status);

  success = 1;
finally:
  PyConfig_Clear(&config);
  if (!success) {
    // This will exit().
    Py_ExitStatusException(status);
  }
}

int
main(int argc, char** argv)
{
  initialize_python();
  emscripten_exit_with_live_runtime();
  // More convenient to construct a multiline string from Javascript than in C,
  // so leave the actual action in pre.js
  return 0;
}

