import subprocess


def format_called_process_error(e: subprocess.CalledProcessError) -> str:
    """Helper to convert a CalledProcessError to an error message.

    >>> format_called_process_error(subprocess.CalledProcessError(
    ...     1, ['cargo', 'foo bar'], 'message', None
    ... ))
    "`cargo 'foo bar'` failed with code 1\\n-- Output captured from stdout:\\nmessage"
    >>> format_called_process_error(subprocess.CalledProcessError(
    ...    -1, ['cargo'], 'stdout', 'stderr'
    ... ))
    '`cargo` failed with code -1\\n-- Output captured from stdout:\\nstdout\\n-- Output captured from stderr:\\nstderr'
    """
    command = " ".join(_quote_whitespace(arg) for arg in e.cmd)
    message = f"""`{command}` failed with code {e.returncode}
-- Output captured from stdout:
{e.stdout}"""

    if e.stderr is not None:
        message += f"""
-- Output captured from stderr:
{e.stderr}"""

    return message


def _quote_whitespace(string: str) -> str:
    if " " in string:
        return f"'{string}'"
    else:
        return string
