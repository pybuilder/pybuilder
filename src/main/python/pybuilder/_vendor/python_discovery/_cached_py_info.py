"""Acquire Python information via subprocess interrogation with multi-level caching."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pkgutil
import secrets
import subprocess  # ruff:ignore[suspicious-subprocess-import]
import sys
import tempfile
from collections import OrderedDict
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from shlex import quote
from subprocess import Popen, TimeoutExpired  # ruff:ignore[suspicious-subprocess-import]
from typing import TYPE_CHECKING, Final

from ._cache import NoOpCache
from ._py_info import PythonInfo
from ._py_info_collect import MIN_INTERROGATE_VERSION, UNSUPPORTED_EXIT_CODE, UNSUPPORTED_MARKER

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping
    from typing import TypedDict

    from ._cache import ContentStore, PyInfoCache

    class CacheEntryMeta(TypedDict):
        """Identity of a cached interrogation result: the queried binary and the script that produced it."""

        st_mtime: float
        path: str
        hash: str | None


_CACHE: OrderedDict[Path, PythonInfo | Exception] = OrderedDict()
_CACHE[Path(sys.executable)] = PythonInfo()
_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_PY_INFO_SCRIPT: Final[Path] = Path(__file__).resolve().parent / "_py_info_collect.py"


class _UnsupportedInterpreterError(RuntimeError):
    """The interpreter is older than the interrogation script supports; retrying cannot help."""


def from_exe(  # ruff:ignore[too-many-arguments]
    cls: type[PythonInfo],
    cache: PyInfoCache | None,
    exe: str,
    env: Mapping[str, str] | None = None,
    *,
    raise_on_error: bool = True,
    ignore_cache: bool = False,
) -> PythonInfo | None:
    env = os.environ if env is None else env
    result = _get_from_cache(cls, cache, exe, env, ignore_cache=ignore_cache)
    if isinstance(result, Exception):
        if raise_on_error:
            raise result
        _LOGGER.info("%s", result)
        result = None
    return result


def _get_from_cache(
    cls: type[PythonInfo],
    cache: PyInfoCache | None,
    exe: str,
    env: Mapping[str, str],
    *,
    ignore_cache: bool = True,
) -> PythonInfo | Exception:
    exe_path = Path(exe)
    if not ignore_cache and exe_path in _CACHE:
        result = _CACHE[exe_path]
    else:
        py_info = _get_via_file_cache(cls, cache, exe_path, exe, env)
        result = _CACHE[exe_path] = py_info
    if isinstance(result, PythonInfo):
        result.executable = exe
    return result


def _get_via_file_cache(
    cls: type[PythonInfo],
    cache: PyInfoCache | None,
    path: Path,
    exe: str,
    env: Mapping[str, str],
) -> PythonInfo | Exception:
    path_text = str(path)
    try:
        path_modified = path.stat().st_mtime
    except OSError:
        path_modified = -1
    try:
        py_info_hash: str | None = _script_hash()
    except OSError:
        py_info_hash = None

    resolved_cache = cache if cache is not None else NoOpCache()
    py_info_store = resolved_cache.py_info(path)
    entry_meta: CacheEntryMeta = {"st_mtime": path_modified, "path": path_text, "hash": py_info_hash}
    with py_info_store.locked():
        cached = _read_cache_entry(cls, py_info_store, entry_meta)
        if isinstance(cached, _UnsupportedInterpreterError):
            return cached
        py_info = cached
        if py_info is None:
            failure, py_info = _run_subprocess(cls, exe, env)
            if failure is not None and not isinstance(failure, _UnsupportedInterpreterError):
                _LOGGER.debug("first subprocess attempt failed for %s (%s), retrying", exe, failure)
                failure, py_info = _run_subprocess(cls, exe, env)
            if isinstance(failure, _UnsupportedInterpreterError):
                _LOGGER.warning("%s", failure)  # the verdict is permanent, warn once and remember it
                py_info_store.write({**entry_meta, "unsupported": str(failure)})
                return failure
            if failure is not None:
                return failure
            if py_info is not None:
                py_info_store.write({**entry_meta, "content": py_info.to_dict()})
    if py_info is None:
        msg = f"{exe} failed to produce interpreter info"
        return RuntimeError(msg)
    return py_info


def _read_cache_entry(
    cls: type[PythonInfo],
    py_info_store: ContentStore,
    entry_meta: CacheEntryMeta,
) -> PythonInfo | _UnsupportedInterpreterError | None:
    if not py_info_store.exists() or (data := py_info_store.read()) is None:
        return None
    if all(data.get(key) == value for key, value in entry_meta.items()):
        if isinstance(unsupported := data.get("unsupported"), str):
            return _UnsupportedInterpreterError(unsupported)
        if isinstance(content := data.get("content"), dict):
            return _load_cached_py_info(cls, py_info_store, content)
    py_info_store.remove()
    return None


def _load_cached_py_info(
    cls: type[PythonInfo],
    py_info_store: ContentStore,
    content: dict,
) -> PythonInfo | None:
    try:
        py_info = cls.from_dict(content.copy())
    except (KeyError, TypeError):
        py_info_store.remove()
        return None
    if (sys_exe := py_info.system_executable) is not None and not Path(sys_exe).exists():
        py_info_store.remove()
        return None
    return py_info


@lru_cache(maxsize=1)
def _script_hash() -> str:
    return hashlib.sha256(_PY_INFO_SCRIPT.read_bytes()).hexdigest()


COOKIE_LENGTH: Final[int] = 32


def gen_cookie() -> str:
    return secrets.token_hex(COOKIE_LENGTH // 2)


@contextmanager
def _resolve_py_info_script() -> Generator[Path]:
    if _PY_INFO_SCRIPT.is_file():
        yield _PY_INFO_SCRIPT
    else:
        data = pkgutil.get_data(__package__ or __name__, _PY_INFO_SCRIPT.name)
        if data is None:
            msg = f"cannot locate {_PY_INFO_SCRIPT.name} for subprocess interrogation"
            raise FileNotFoundError(msg)
        fd, tmp = tempfile.mkstemp(suffix=".py")
        try:
            os.write(fd, data)
            os.close(fd)
            yield Path(tmp)
        finally:
            Path(tmp).unlink()


def _extract_between_cookies(out: str, start_cookie: str, end_cookie: str) -> tuple[str, str, int, int]:
    """Extract payload between reversed cookie markers, forwarding any surrounding output to stdout."""
    raw_out = out
    out_starts = out.find(start_cookie[::-1])
    if out_starts > -1:
        if pre_cookie := out[:out_starts]:
            sys.stdout.write(pre_cookie)
        out = out[out_starts + COOKIE_LENGTH :]
    out_ends = out.find(end_cookie[::-1])
    if out_ends > -1:
        if post_cookie := out[out_ends + COOKIE_LENGTH :]:
            sys.stdout.write(post_cookie)
        out = out[:out_ends]
    return out, raw_out, out_starts, out_ends


def _run_subprocess(
    cls: type[PythonInfo],
    exe: str,
    env: Mapping[str, str],
) -> tuple[Exception | None, PythonInfo | None]:
    start_cookie = gen_cookie()
    end_cookie = gen_cookie()
    timeout = float(env.get("PY_DISCOVERY_TIMEOUT", "15"))
    with _resolve_py_info_script() as py_info_script:
        cmd = [exe, str(py_info_script), start_cookie, end_cookie]
        env = dict(env)
        env.pop("__PYVENV_LAUNCHER__", None)
        env["PYTHONUTF8"] = "1"
        _LOGGER.debug("get interpreter info via cmd: %s", LogCmd(cmd))
        try:
            process = Popen(  # ruff:ignore[subprocess-without-shell-equals-true]
                cmd,
                universal_newlines=True,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                env=env,
                encoding="utf-8",
                errors="backslashreplace",
            )
            out, err = process.communicate(timeout=timeout)
            code = process.returncode
        except TimeoutExpired:
            process.kill()
            process.communicate()
            out, err, code = "", "timed out", -1
        except OSError as os_error:
            out, err, code = "", os_error.strerror, os_error.errno
    if code != 0:
        return _query_failure(exe, out, err, code), None
    out, raw_out, out_starts, out_ends = _extract_between_cookies(out, start_cookie, end_cookie)
    try:
        result = cls.from_json(out)
        result.executable = exe
    except json.JSONDecodeError as exc:
        _LOGGER.warning(
            "subprocess %s returned invalid JSON; raw stdout %d chars, start cookie %s, end cookie %s, "
            "parsed output %d chars: %r",
            exe,
            len(raw_out),
            "found" if out_starts > -1 else "missing",
            "found" if out_ends > -1 else "missing",
            len(out),
            out[:200] if out else "<empty>",
        )
        msg = f"{exe} returned invalid JSON (exit code {code}){f', stderr: {err!r}' if err else ''}"
        failure = RuntimeError(msg)
        failure.__cause__ = exc
        return failure, None
    return None, result


def _query_failure(exe: str, out: str, err: str | None, code: int | None) -> RuntimeError:
    # the gate's exit code and stderr marker must both be present: either alone can collide, an errno of 79 from a
    # failed exec or a shim that echoes the marker phrase, but only the gate produces the combination
    if code == UNSUPPORTED_EXIT_CODE and err is not None and (at := err.find(UNSUPPORTED_MARKER)) != -1:
        version = err[at + len(UNSUPPORTED_MARKER) :].split() or ["unknown"]
        floor = ".".join(str(i) for i in MIN_INTERROGATE_VERSION)
        msg = f"{exe} is Python {version[0]}, older than the minimum {floor} python-discovery can query"
        return _UnsupportedInterpreterError(msg)
    msg = f"{exe} with code {code}{f' out: {out!r}' if out else ''}{f' err: {err!r}' if err else ''}"
    return RuntimeError(f"failed to query {msg}")


class LogCmd:
    def __init__(self, cmd: list[str], env: Mapping[str, str] | None = None) -> None:
        self.cmd = cmd
        self.env = env

    def __repr__(self) -> str:
        cmd_repr = " ".join(quote(str(c)) for c in self.cmd)
        if self.env is not None:
            cmd_repr = f"{cmd_repr} env of {self.env!r}"
        return cmd_repr


def clear(cache: PyInfoCache) -> None:
    cache.py_info_clear()
    _CACHE.clear()


__all__ = [
    "LogCmd",
    "clear",
    "from_exe",
]
