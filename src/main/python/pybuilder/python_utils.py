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

import fnmatch
import os
import platform
import re
import sys
import traceback
from collections import OrderedDict

try:
    basestring = basestring
except NameError:
    basestring = str

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

StringIO = StringIO


def is_windows(platform=sys.platform, win_platforms={"win32", "cygwin", "msys"}):
    return platform in win_platforms


PY2 = sys.version_info[0] < 3
IS_PYPY = '__pypy__' in sys.builtin_module_names
IS_WIN = is_windows()


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

    if IS_WIN:
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
_mp_billiard_pyb_env = None  # This will be patched at runtime

_old_billiard_spawn_passfds = None  # This will be patched at runtime
_installed_tblib = False

# Billiard doesn't work on Win32
if PY2:
    if IS_WIN:
        # Python 2.7 on Windows already only works with spawn

        from multiprocessing import log_to_stderr as mp_log_to_stderr
        from multiprocessing.reduction import ForkingPickler as mp_ForkingPickler

        _mp_get_context = _mp_get_context_win32_py2

    # Python 2 on *nix uses Billiard to be patched later
else:
    # On all of Python 3s use multiprocessing

    from multiprocessing import log_to_stderr as mp_log_to_stderr, get_context as _mp_get_context
    from multiprocessing.reduction import ForkingPickler as mp_ForkingPickler


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


def _patched_billiard_spawnv_passfds(path, args, passfds):
    global _mp_billiard_plugin_dir, _old_billiard_spawn_passfds

    try:
        script_index = args.index("-c") + 1
        script = args[script_index]
        additional_path = []
        add_env_to_path(_mp_billiard_pyb_env, additional_path)
        args[script_index] = ";".join(("import sys", "sys.path.extend(%r)" % additional_path, script))
    except ValueError:
        # We were unable to find the "-c", which means we likely don't care
        pass

    return _old_billiard_spawn_passfds(path, args, passfds)


def patch_mp():
    install_tblib()

    global _mp_get_context

    if not _mp_get_context:
        if PY2 and not IS_WIN:
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


def add_env_to_path(python_env, sys_path):
    """type: (PythonEnv, List(str)) -> None
    Adds venv directories to sys.path-like collection
    """
    for path in python_env.site_paths:
        if path not in sys_path:
            sys_path.append(path)


if PY2:
    def _py2_glob(pathname, recursive=False):
        """Return a list of paths matching a pathname pattern.

        The pattern may contain simple shell-style wildcards a la
        fnmatch. However, unlike fnmatch, filenames starting with a
        dot are special cases that are not matched by '*' and '?'
        patterns.

        If recursive is true, the pattern '**' will match any files and
        zero or more directories and subdirectories.
        """
        return list(_py2_iglob(pathname, recursive=recursive))


    def _py2_iglob(pathname, recursive=False):
        """Return an iterator which yields the paths matching a pathname pattern.

        The pattern may contain simple shell-style wildcards a la
        fnmatch. However, unlike fnmatch, filenames starting with a
        dot are special cases that are not matched by '*' and '?'
        patterns.

        If recursive is true, the pattern '**' will match any files and
        zero or more directories and subdirectories.
        """
        it = _iglob(pathname, recursive, False)
        if recursive and _isrecursive(pathname):
            s = next(it)  # skip empty string
            assert not s
        return it


    def _iglob(pathname, recursive, dironly):
        dirname, basename = os.path.split(pathname)
        if not has_magic(pathname):
            assert not dironly
            if basename:
                if os.path.lexists(pathname):
                    yield pathname
            else:
                # Patterns ending with a slash should match only directories
                if os.path.isdir(dirname):
                    yield pathname
            return
        if not dirname:
            if recursive and _isrecursive(basename):
                for v in _glob2(dirname, basename, dironly):
                    yield v
            else:
                for v in _glob1(dirname, basename, dironly):
                    yield v
            return
        # `os.path.split()` returns the argument itself as a dirname if it is a
        # drive or UNC path.  Prevent an infinite recursion if a drive or UNC path
        # contains magic characters (i.e. r'\\?\C:').
        if dirname != pathname and has_magic(dirname):
            dirs = _iglob(dirname, recursive, True)
        else:
            dirs = [dirname]
        if has_magic(basename):
            if recursive and _isrecursive(basename):
                glob_in_dir = _glob2
            else:
                glob_in_dir = _glob1
        else:
            glob_in_dir = _glob0
        for dirname in dirs:
            for name in glob_in_dir(dirname, basename, dironly):
                yield os.path.join(dirname, name)


    def _glob1(dirname, pattern, dironly):
        names = list(_iterdir(dirname, dironly))
        if not _ishidden(pattern):
            names = (x for x in names if not _ishidden(x))
        return fnmatch.filter(names, pattern)


    def _glob0(dirname, basename, dironly):
        if not basename:
            # `os.path.split()` returns an empty basename for paths ending with a
            # directory separator.  'q*x/' should match only directories.
            if os.path.isdir(dirname):
                return [basename]
        else:
            if os.path.lexists(os.path.join(dirname, basename)):
                return [basename]
        return []


    def glob0(dirname, pattern):
        return _glob0(dirname, pattern, False)


    def glob1(dirname, pattern):
        return _glob1(dirname, pattern, False)


    def _glob2(dirname, pattern, dironly):
        assert _isrecursive(pattern)
        yield pattern[:0]
        for v in _rlistdir(dirname, dironly):
            yield v


    def _iterdir(dirname, dironly):
        if not dirname:
            if isinstance(dirname, bytes):
                dirname = os.curdir.decode('ASCII')
            else:
                dirname = os.curdir
        try:
            for entry in os.listdir(dirname):
                try:
                    if not dironly or os.path.isdir(os.path.join(dirname, entry)):
                        yield entry
                except OSError:
                    pass
        except OSError:
            return


    def _rlistdir(dirname, dironly):
        names = list(_iterdir(dirname, dironly))
        for x in names:
            if not _ishidden(x):
                yield x
                path = os.path.join(dirname, x) if dirname else x
                for y in _rlistdir(path, dironly):
                    yield os.path.join(x, y)


    magic_check = re.compile('([*?[])')
    magic_check_bytes = re.compile(b'([*?[])')


    def has_magic(s):
        if isinstance(s, bytes):
            match = magic_check_bytes.search(s)
        else:
            match = magic_check.search(s)
        return match is not None


    def _ishidden(path):
        return path[0] in ('.', b'.'[0])


    def _isrecursive(pattern):
        if isinstance(pattern, bytes):
            return pattern == b'**'
        else:
            return pattern == '**'


    glob = _py2_glob
    iglob = _py2_iglob
else:
    from glob import glob, iglob

try:
    from os import symlink
except ImportError:
    import ctypes

    csl = ctypes.windll.kernel32.CreateSymbolicLinkW
    csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    csl.restype = ctypes.c_ubyte


    def symlink(source, link_name, target_is_directory=False):
        flags = 1 if target_is_directory else 0
        flags += 2
        if csl(link_name, source, flags) == 0:
            raise ctypes.WinError()

sys_executable_suffix = sys.executable[len(sys.exec_prefix) + 1:]

python_specific_dir_name = "%s-%s" % (platform.python_implementation().lower(),
                                      ".".join(str(f) for f in sys.version_info))

_, _venv_python_exename = os.path.split(os.path.abspath(getattr(sys, "_base_executable", sys.executable)))

__all__ = ["glob", "iglob"]
