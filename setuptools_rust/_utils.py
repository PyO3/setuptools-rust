import subprocess
from typing import Any, Optional, Union, cast


class Env:
    """Allow using ``functools.lru_cache`` with an environment variable dictionary.

    Dictionaries are unhashable, but ``functools.lru_cache`` needs all parameters to
    be hashable, which we solve which a custom ``__hash__``."""

    env: Optional[dict[str, str]]

    def __init__(self, env: Optional[dict[str, str]]):
        self.env = env

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Env):
            return False
        return self.env == other.env

    def __hash__(self) -> int:
        if self.env is not None:
            return hash(tuple(sorted(self.env.items())))
        else:
            return hash(None)


def run_subprocess(
    *args: Any, env: Union[Env, dict[str, str], None], **kwargs: Any
) -> subprocess.CompletedProcess:
    """Wrapper around subprocess.run that requires a decision to pass env."""
    if isinstance(env, Env):
        env = env.env
    kwargs["env"] = env
    return subprocess.run(*args, **kwargs)  # noqa: TID251 # this is a wrapper to implement the rule


def check_subprocess_output(
    *args: Any, env: Union[Env, dict[str, str], None], **kwargs: Any
) -> str:
    """Wrapper around subprocess.run that requires a decision to pass env."""
    if isinstance(env, Env):
        env = env.env
    kwargs["env"] = env
    return cast(str, subprocess.check_output(*args, **kwargs))  # noqa: TID251 # this is a wrapper to implement the rule


def format_called_process_error(
    e: subprocess.CalledProcessError,
    *,
    include_stdout: bool = True,
    include_stderr: bool = True,
) -> str:
    """Helper to convert a CalledProcessError to an error message.

    If `include_stdout` or `include_stderr` are True (the default), the
    respective output stream will be added to the error message (if
    present in the exception).

    >>> format_called_process_error(subprocess.CalledProcessError(
    ...     777, ['ls', '-la'], None, None
    ... ))
    '`ls -la` failed with code 777'
    >>> format_called_process_error(subprocess.CalledProcessError(
    ...     1, ['cargo', 'foo bar'], 'message', None
    ... ))
    "`cargo 'foo bar'` failed with code 1\\n-- Output captured from stdout:\\nmessage"
    >>> format_called_process_error(subprocess.CalledProcessError(
    ...     1, ['cargo', 'foo bar'], 'message', None
    ... ), include_stdout=False)
    "`cargo 'foo bar'` failed with code 1"
    >>> format_called_process_error(subprocess.CalledProcessError(
    ...    -1, ['cargo'], 'stdout', 'stderr'
    ... ))
    '`cargo` failed with code -1\\n-- Output captured from stdout:\\nstdout\\n-- Output captured from stderr:\\nstderr'
    """
    command = " ".join(_quote_whitespace(arg) for arg in e.cmd)
    message = f"`{command}` failed with code {e.returncode}"
    if include_stdout and e.stdout is not None:
        message += f"""
-- Output captured from stdout:
{e.stdout}"""

    if include_stderr and e.stderr is not None:
        message += f"""
-- Output captured from stderr:
{e.stderr}"""

    return message


def _quote_whitespace(string: str) -> str:
    if " " in string:
        return f"'{string}'"
    else:
        return string
