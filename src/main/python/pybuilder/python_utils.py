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
from os.path import normcase as nc, join as jp

try:
    basestring = basestring
except NameError:
    basestring = str

PY2 = sys.version_info[0] < 3


def _py2_makedirs(name, mode=0o777, exist_ok=False):
    return os.makedirs(name, mode)


def _py2_which(cmd, mode=os.F_OK | os.X_OK, path=None):
    """Given a command, mode, and a PATH string, return the path which
    conforms to the given mode on the PATH, or None if there is no such
    file.

    `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
    of os.environ.get("PATH"), or can be overridden with a custom search
    path.

    """

    # Check that a given file can be accessed with the correct mode.
    # Additionally check that `file` is not a directory, as on Windows
    # directories pass the os.access check.
    def _access_check(fn, mode):
        return (os.path.exists(fn) and os.access(fn, mode)
                and not os.path.isdir(fn))

    # If we're given a path with a directory part, look it up directly rather
    # than referring to PATH directories. This includes checking relative to the
    # current directory, e.g. ./script
    if os.path.dirname(cmd):
        if _access_check(cmd, mode):
            return cmd
        return None

    if path is None:
        path = os.environ.get("PATH", os.defpath)
    if not path:
        return None
    path = path.split(os.pathsep)

    if sys.platform == "win32":
        # The current directory takes precedence on Windows.
        if os.curdir not in path:
            path.insert(0, os.curdir)

        # PATHEXT is necessary to check on Windows.
        pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
        # See if the given file matches any of the expected path extensions.
        # This will allow us to short circuit when given "python.exe".
        # If it does match, only test that one, otherwise we have to try
        # others.
        if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
            files = [cmd]
        else:
            files = [cmd + ext for ext in pathext]
    else:
        # On other platforms you don't have things like PATHEXT to tell you
        # what file suffixes are executable, so just pass on cmd as-is.
        files = [cmd]

    seen = set()
    for dir in path:
        normdir = os.path.normcase(dir)
        if normdir not in seen:
            seen.add(normdir)
            for thefile in files:
                name = os.path.join(dir, thefile)
                if _access_check(name, mode):
                    return name
    return None


if PY2:  # if major is less than 3
    from .excp_util_2 import raise_exception, is_string


    def save_tb(ex):
        tb = sys.exc_info()[2]
        setattr(ex, "__traceback__", tb)


    is_string = is_string

    makedirs = _py2_makedirs
    which = _py2_which
else:
    from .excp_util_3 import raise_exception, is_string

    from shutil import which


    def save_tb(ex):
        pass


    is_string = is_string
    makedirs = os.makedirs
    which = which

odict = OrderedDict


def _mp_get_context_win32_py2(context_name):
    if context_name != "spawn":
        raise RuntimeError("only spawn is supported")

    import multiprocessing
    return multiprocessing


_mp_get_context = None  # This will be patched at runtime
mp_ForkingPickler = None  # This will be patched at runtime
mp_log_to_stderr = None  # This will be patched at runtime
_mp_billiard_plugin_dir = None  # This will be patched at runtime

_old_billiard_spawn_passfds = None  # This will be patched at runtime
_installed_tblib = False

# Billiard doesn't work on Win32
if PY2:
    if sys.platform == "win32":
        # Python 2.7 on Windows already only works with spawn

        import multiprocessing
        import multiprocessing.queues

        from multiprocessing import log_to_stderr as mp_log_to_stderr
        from multiprocessing.reduction import ForkingPickler as mp_ForkingPickler

        _mp_get_context = _mp_get_context_win32_py2

    # Python 2 on *nix uses Billiard to be patched later
else:
    # On all of Python 3s use multiprocessing

    from multiprocessing import log_to_stderr as mp_log_to_stderr, get_context as _mp_get_context
    from multiprocessing.reduction import ForkingPickler as mp_ForkingPickler


def patch_mp_plugin_dir(plugin_dir):
    global _mp_billiard_plugin_dir

    if not _mp_billiard_plugin_dir:
        _mp_billiard_plugin_dir = plugin_dir


def install_tblib():
    global _installed_tblib

    if not _installed_tblib:
        from pybuilder._vendor.tblib import pickling_support

        pickling_support.install()
        _installed_tblib = True


def _patched_billiard_spawnv_passfds(path, args, passfds):
    global _mp_billiard_plugin_dir, _old_billiard_spawn_passfds

    try:
        script_index = args.index("-c") + 1
        script = args[script_index]
        additional_path = []
        add_env_to_path(_mp_billiard_plugin_dir, additional_path)
        args[script_index] = ";".join(("import sys", "sys.path.extend(%r)" % additional_path, script))
    except ValueError:
        # We were unable to find the "-c", which means we likely don't care
        pass

    return _old_billiard_spawn_passfds(path, args, passfds)


def patch_mp():
    install_tblib()

    global _mp_get_context

    if not _mp_get_context:
        if PY2 and sys.platform != "win32":
            from billiard import get_context, log_to_stderr, compat, popen_spawn_posix as popen_spawn
            from billiard.reduction import ForkingPickler

            global mp_ForkingPickler, mp_log_to_stderr, _old_billiard_spawn_passfds

            _mp_get_context = get_context
            mp_ForkingPickler = ForkingPickler
            mp_log_to_stderr = log_to_stderr

            _old_billiard_spawn_passfds = compat.spawnv_passfds
            compat.spawnv_passfds = _patched_billiard_spawnv_passfds
            popen_spawn.spawnv_passfds = _patched_billiard_spawnv_passfds


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


sys_executable_suffix = sys.executable[len(sys.exec_prefix) + 1:]

python_specific_dir_name = "%s-%s" % (platform.python_implementation().lower(),
                                      ".".join(str(f) for f in sys.version_info))

venv_symlinks = os.name == "posix"
_, _venv_python_exename = os.path.split(os.path.abspath(getattr(sys, "_base_executable", sys.executable)))
venv_binname = "Scripts" if sys.platform == "win32" else "bin"


def add_env_to_path(env_dir, sys_path):
    """Adds venv directories to sys.path-like collection"""
    for path in getsitepaths(env_dir):
        if path not in sys_path:
            sys_path.append(path)


def venv_python_executable(env_dir):
    """Binary Python executable for a specific virtual environment"""
    candidate = jp(env_dir, venv_binname, _venv_python_exename)

    if sys.platform == "win32":
        # On Windows python.exe could be in PythonXY/ or venv/Scripts/
        if not os.path.exists(candidate):
            alternative = jp(env_dir, _venv_python_exename)
            if os.path.exists(alternative):
                candidate = alternative

    return nc(candidate)


if sys.version_info[0] < 3:
    def getsitepaths(prefix):
        if sys.platform in ('os2emx', 'riscos'):
            yield os.path.join(prefix, "Lib", "site-packages")
        elif os.sep == '/':
            yield os.path.join(prefix, "lib",
                               "python" + sys.version[:3],
                               "site-packages")
            yield os.path.join(prefix, "lib", "site-python")
        else:
            yield prefix
            yield os.path.join(prefix, "lib", "site-packages")

else:
    def getsitepaths(prefix):
        if os.sep == '/':
            yield os.path.join(prefix, "lib",
                               "python%d.%d" % sys.version_info[:2],
                               "site-packages")
        else:
            yield prefix
            yield os.path.join(prefix, "lib", "site-packages")

        if sys.platform == "darwin":
            # for framework builds *only* we add the standard Apple
            # locations.
            from sysconfig import get_config_var
            framework = get_config_var("PYTHONFRAMEWORK")
            if framework:
                yield os.path.join("/Library", framework,
                                   '%d.%d' % sys.version_info[:2], "site-packages")


def is_windows():
    return any(win_platform in sys.platform for win_platform in ("win32", "cygwin", "msys"))
