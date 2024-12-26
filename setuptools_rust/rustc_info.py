from __future__ import annotations

import subprocess
from setuptools.errors import PlatformError
from functools import lru_cache
from typing import Dict, List, NewType, Optional, TYPE_CHECKING

from ._utils import Env

if TYPE_CHECKING:
    from semantic_version import Version


def get_rust_version(env: Optional[Env]) -> Optional[Version]:  # type: ignore[no-any-unimported]
    try:
        # first line of rustc -Vv is something like
        # rustc 1.61.0 (fe5b13d68 2022-05-18)
        from semantic_version import Version

        return Version(_rust_version(env).split(" ")[1])
    except (subprocess.CalledProcessError, OSError):
        return None


_HOST_LINE_START = "host: "


def get_rust_host(env: Optional[Env]) -> str:
    # rustc -Vv has a line denoting the host which cargo uses to decide the
    # default target, e.g.
    # host: aarch64-apple-darwin
    for line in _rust_version_verbose(env).splitlines():
        if line.startswith(_HOST_LINE_START):
            return line[len(_HOST_LINE_START) :].strip()
    raise PlatformError("Could not determine rust host")


RustCfgs = NewType("RustCfgs", Dict[str, Optional[str]])


def get_rustc_cfgs(target_triple: Optional[str], env: Optional[Env]) -> RustCfgs:
    cfgs = RustCfgs({})
    for entry in get_rust_target_info(target_triple, env):
        maybe_split = entry.split("=", maxsplit=1)
        if len(maybe_split) == 2:
            cfgs[maybe_split[0]] = maybe_split[1].strip('"')
        else:
            assert len(maybe_split) == 1
            cfgs[maybe_split[0]] = None
    return cfgs


@lru_cache()
def get_rust_target_info(target_triple: Optional[str], env: Optional[Env]) -> List[str]:
    cmd = ["rustc", "--print", "cfg"]
    if target_triple:
        cmd.extend(["--target", target_triple])
    output = subprocess.check_output(cmd, text=True, env=env.env)
    return output.splitlines()


@lru_cache()
def get_rust_target_list(env: Optional[Env]) -> List[str]:
    output = subprocess.check_output(
        ["rustc", "--print", "target-list"], text=True, env=env.env
    )
    return output.splitlines()


@lru_cache()
def _rust_version(env: Optional[Env]) -> str:
    return subprocess.check_output(["rustc", "-V"], text=True, env=env.env)


@lru_cache()
def _rust_version_verbose(env: Optional[Env]) -> str:
    return subprocess.check_output(["rustc", "-Vv"], text=True, env=env.env)
