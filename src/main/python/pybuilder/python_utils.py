#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2020 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import platform
import sys
import traceback
from collections import OrderedDict
from io import StringIO


def is_windows(platform=sys.platform, win_platforms={"win32", "cygwin", "msys"}):
    return platform in win_platforms


StringIO = StringIO
IS_PYPY = '__pypy__' in sys.builtin_module_names
IS_WIN = is_windows()


def raise_exception(ex, tb):
    raise ex.with_traceback(tb)


def is_string(val):
    return isinstance(val, str)


from shutil import which  # noqa: E402


def save_tb(ex):
    pass


is_string = is_string
makedirs = os.makedirs
which = which

odict = OrderedDict

_mp_get_context = None  # This will be patched at runtime
mp_ForkingPickler = None  # This will be patched at runtime
mp_log_to_stderr = None  # This will be patched at runtime
_mp_billiard_pyb_env = None  # This will be patched at runtime

_old_billiard_spawn_passfds = None  # This will be patched at runtime
_installed_tblib = False

from multiprocessing import log_to_stderr as mp_log_to_stderr, get_context as _mp_get_context  # noqa: E402
from multiprocessing.reduction import ForkingPickler as mp_ForkingPickler  # noqa: E402


def patch_mp_pyb_env(pyb_env):
    global _mp_billiard_pyb_env

    if not _mp_billiard_pyb_env:
        _mp_billiard_pyb_env = pyb_env


def install_tblib():
    global _installed_tblib

    if not _installed_tblib:
        from pybuilder._vendor.tblib import pickling_support

        pickling_support.install()
        _installed_tblib = True


def patch_mp():
    install_tblib()


def mp_get_context(context):
    global _mp_get_context
    return _mp_get_context(context)


mp_ForkingPickler = mp_ForkingPickler
mp_log_to_stderr = mp_log_to_stderr
_mp_get_context = _mp_get_context


def _instrumented_target(q, target, *args, **kwargs):
    patch_mp()

    ex = tb = None
    try:
        send_value = (target(*args, **kwargs), None, None)
    except Exception:
        _, ex, tb = sys.exc_info()
        send_value = (None, ex, tb)

    try:
        q.put(send_value)
    except Exception:
        _, send_ex, send_tb = sys.exc_info()
        e_out = Exception(str(send_ex), send_tb, None if ex is None else str(ex), tb)
        q.put(e_out)


def spawn_process(target=None, args=(), kwargs={}, group=None, name=None):
    """
    Forks a child, making sure that all exceptions from the child are safely sent to the parent
    If a target raises an exception, the exception is re-raised in the parent process
    @return tuple consisting of process exit code and target's return value
    """
    ctx = mp_get_context("spawn")

    q = ctx.SimpleQueue()
    p = ctx.Process(group=group, target=_instrumented_target, name=name, args=[q, target] + list(args), kwargs=kwargs)
    p.start()
    result = q.get()
    p.join()
    if isinstance(result, tuple):
        if result[1]:
            raise_exception(result[1], result[2])
        return p.exitcode, result[0]
    else:
        msg = "Fatal error occurred in the forked process %s: %s" % (p, result.args[0])
        if result.args[2]:
            chained_message = "This error masked the send error '%s':\n%s" % (
                result.args[2], "".join(traceback.format_tb(result.args[3])))
            msg += "\n" + chained_message
        ex = Exception(msg)
        raise_exception(ex, result.args[1])


def prepend_env_to_path(python_env, sys_path):
    """type: (PythonEnv, List(str)) -> None
    Prepend venv directories to sys.path-like collection
    """
    for path in reversed(python_env.site_paths):
        if path not in sys_path:
            sys_path.insert(0, path)


def add_env_to_path(python_env, sys_path):
    """type: (PythonEnv, List(str)) -> None
    Adds venv directories to sys.path-like collection
    """
    for path in python_env.site_paths:
        if path not in sys_path:
            sys_path.append(path)


from glob import glob, iglob, escape  # noqa: E402

from os import symlink  # noqa: E402

symlink = symlink

sys_executable_suffix = sys.executable[len(sys.exec_prefix) + 1:]

python_specific_dir_name = "%s-%s" % (platform.python_implementation().lower(),
                                      ".".join(str(f) for f in sys.version_info))

_, _venv_python_exename = os.path.split(os.path.abspath(getattr(sys, "_base_executable", sys.executable)))

__all__ = ["glob", "iglob", "escape"]
