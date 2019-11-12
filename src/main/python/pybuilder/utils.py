#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2019 PyBuilder Team
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

"""
    The PyBuilder utils module.
    Provides generic utilities that can be used by plugins.
"""

import collections
import fnmatch
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import traceback
from collections import OrderedDict
from os.path import normcase as nc, join as jp
from shutil import rmtree
from subprocess import Popen, PIPE

from pybuilder.vendor import virtualenv

try:
    basestring = basestring
except NameError:
    basestring = str

from pybuilder.errors import MissingPrerequisiteException, PyBuilderException


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


def _mp_get_context_win32_py2(context_name):
    if context_name != "spawn":
        raise RuntimeError("only spawn is supported")

    return multiprocessing


if sys.version_info[0] < 3:  # if major is less than 3
    from .excp_util_2 import raise_exception, is_string

    is_string = is_string

    if sys.platform == "win32":
        import multiprocessing
        import multiprocessing.queues

        for name in (name for name in dir(multiprocessing.queues) if name[0].isupper()):
            setattr(multiprocessing, name, getattr(multiprocessing.queues, name))

        _mp_get_context = _mp_get_context_win32_py2
    else:
        _mp_get_context = None  # This will be patched at runtime

    _old_billiard_spawn_passfds = None  # This will be patched at runtime

    makedirs = _py2_makedirs
    which = _py2_which
else:
    from .excp_util_3 import raise_exception, is_string

    from multiprocessing import get_context as _mp_get_context
    from shutil import which

    is_string = is_string
    makedirs = os.makedirs
    which = which

odict = OrderedDict


def get_all_dependencies_for_task(task):
    """
    Returns a list containing all tasks required by the given
    task function (but not the given task itself)
    """
    from pybuilder.reactor import Reactor

    task_name = task.__name__
    execution_manager = Reactor.current_instance().execution_manager
    task_and_all_dependencies = execution_manager.collect_all_transitive_tasks([task_name])
    return [dependency for dependency in task_and_all_dependencies if dependency.name != task_name]


def render_report(report_dict):
    return json.dumps(report_dict, indent=2, sort_keys=True)


def format_timestamp(timestamp):
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def timedelta_in_millis(timedelta):
    return ((timedelta.days * 24 * 60 * 60) + timedelta.seconds) * 1000 + round(timedelta.microseconds / 1000)


def as_list(*whatever):
    """
        Returns a list containing all values given in whatever.
        Each list or tuple will be "unpacked", all other elements
        are added to the resulting list.

        Examples given

        >>> as_list('spam')
        ['spam']

        >>> as_list('spam', 'eggs')
        ['spam', 'eggs']

        >>> as_list(('spam', 'eggs'))
        ['spam', 'eggs']

        >>> as_list(['spam', 'eggs'])
        ['spam', 'eggs']

        >>> as_list(['spam', 'eggs'], ('spam', 'eggs'), 'foo', 'bar')
        ['spam', 'eggs', 'spam', 'eggs', 'foo', 'bar']
    """
    result = []

    for w in whatever:
        if w is None:
            continue
        elif isinstance(w, list):
            result += w
        elif isinstance(w, tuple):
            result += w
        else:
            result.append(w)
    return result


def remove_leading_slash_or_dot_from_path(path):
    if path.startswith('/') or path.startswith('.'):
        return path[1:]
    return path


def remove_python_source_suffix(file_name):
    if file_name.endswith(".py"):
        return file_name[0:-len(".py")]
    return file_name


def discover_modules(source_path, suffix=".py"):
    return discover_modules_matching(source_path, "*{0}".format(suffix))


def discover_modules_matching(source_path, module_glob):
    result = []
    if not module_glob.endswith(".py"):
        module_glob += ".py"
    for module_file_path in discover_files_matching(source_path, module_glob):
        relative_module_file_path = module_file_path.replace(source_path, "")
        relative_module_file_path = relative_module_file_path.replace(os.sep, ".")
        module_file = remove_leading_slash_or_dot_from_path(relative_module_file_path)
        module_name = remove_python_source_suffix(module_file)
        if module_name.endswith(".__init__"):
            module_name = module_name.replace(".__init__", "")
        result.append(module_name)
    return result


def discover_files(start_dir, suffix):
    return discover_files_matching(start_dir, "*{0}".format(suffix))


def discover_files_matching(start_dir, file_glob, exclude_file_glob=None):
    for root, _, files in os.walk(start_dir):
        for file_name in files:
            if exclude_file_glob:
                for exclude_pat in as_list(exclude_file_glob):
                    if fnmatch.fnmatch(file_name, exclude_pat):
                        continue
            if fnmatch.fnmatch(file_name, file_glob):
                yield os.path.join(root, file_name)


def execute_command(command_and_arguments, outfile_name=None, env=None, cwd=None, error_file_name=None, shell=False,
                    no_path_search=False):
    if error_file_name is None and outfile_name:
        error_file_name = outfile_name + ".err"

    out_file_created = False
    error_file_created = False

    if not hasattr(outfile_name, "write"):
        outfile_name = open(outfile_name, "w") if outfile_name else None
        out_file_created = True

    try:
        if not hasattr(error_file_name, "write"):
            error_file_name = open(error_file_name, "w") if error_file_name else None
            error_file_created = True

        try:
            if not shell and sys.platform == "win32" and not is_string(command_and_arguments) and not no_path_search:
                which_cmd = which(command_and_arguments[0], path=env.get("PATH", None) if env else None)
                if which_cmd:
                    command_and_arguments[0] = which_cmd
            process = Popen(command_and_arguments,
                            stdout=outfile_name,
                            stderr=error_file_name,
                            env=env,
                            cwd=cwd,
                            shell=shell)
            return process.wait()
        finally:
            if error_file_name and error_file_created:
                error_file_name.close()
    finally:
        if outfile_name and out_file_created:
            outfile_name.close()


def execute_command_and_capture_output(*command_and_arguments):
    process_handle = Popen(command_and_arguments, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process_handle.communicate()
    stdout, stderr = stdout.decode(sys.stdout.encoding or 'utf-8'), stderr.decode(sys.stderr.encoding or 'utf-8')
    process_return_code = process_handle.returncode
    return process_return_code, stdout, stderr


def tail(file_path, lines=20):
    try:
        import pybuilder._vendor.tailer as tailer
    except ImportError:
        return read_file(file_path)

    with open(file_path) as f:
        return tailer.tail(f, lines)


def tail_log(file_path, lines=20):
    return "\n".join("\t" + l for l in tail(file_path, lines))


def assert_can_execute(command_and_arguments, prerequisite, caller, env):
    with tempfile.NamedTemporaryFile() as f:
        try:
            if sys.platform == "win32" and not is_string(command_and_arguments):
                which_cmd = which(command_and_arguments[0], path=env.get("PATH", None) if env else None)
                if which_cmd:
                    command_and_arguments[0] = which_cmd
            process = subprocess.Popen(command_and_arguments, stdout=f, stderr=f, shell=False, env=env)
            process.wait()
        except OSError:
            raise MissingPrerequisiteException(prerequisite, caller)


def read_file(file_name):
    if hasattr(file_name, "mode"):
        # This is an open file with mode
        file_name.seek(0)
        return file_name.readlines()
    else:
        with open(file_name, "r") as file_handle:
            return file_handle.readlines()


def write_file(file_name, *lines):
    with open(file_name, "w") as file_handle:
        file_handle.writelines(lines)


class Timer(object):
    @staticmethod
    def start():
        return Timer()

    def __init__(self):
        self.start_time = time.time()
        self.end_time = None

    def stop(self):
        self.end_time = time.time()

    def get_millis(self):
        if self.end_time is None:
            raise PyBuilderException("Timer is running.")
        return int((self.end_time - self.start_time) * 1000)


def apply_on_files(start_directory, closure, globs, *additional_closure_arguments, **keyword_closure_arguments):
    glob_expressions = list(map(lambda g: GlobExpression(g), globs))

    for root, _, file_names in os.walk(start_directory):
        for file_name in file_names:
            absolute_file_name = os.path.join(root, file_name)
            relative_file_name = absolute_file_name.replace(start_directory, "")[1:]

            for glob_expression in glob_expressions:
                if glob_expression.matches(relative_file_name):
                    closure(absolute_file_name,
                            relative_file_name,
                            *additional_closure_arguments,
                            **keyword_closure_arguments)


class GlobExpression(object):
    def __init__(self, expression):
        self.expression = expression
        self.regex = "^" + expression.replace("**", ".+").replace("*", "[^/]*") + "$"
        self.pattern = re.compile(self.regex)

    def matches(self, path):
        if self.pattern.match(path):
            return True
        return False


def mkdir(directory):
    """
    Tries to create the directory denoted by the given name. If it exists and is a directory, nothing will be created
    and no error is raised. If it exists as a file a PyBuilderException is raised. Otherwise the directory incl.
    all parents is created.
    """

    if os.path.exists(directory):
        if os.path.isfile(directory):
            message = "Unable to created directory '%s': A file with that name already exists"
            raise PyBuilderException(message, directory)
        return
    makedirs(directory, exist_ok=True)


def is_windows():
    return any(win_platform in sys.platform for win_platform in ("win32", "cygwin", "msys"))


def fake_windows_fork(group, target, name, args, kwargs):
    return 0, target(*args, **kwargs)


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


def fork_process(logger, group=None, target=None, name=None, args=(), kwargs={}):
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


def is_notstr_iterable(obj):
    """Checks if obj is iterable, but not a string"""
    return not isinstance(obj, basestring) and isinstance(obj, collections.Iterable)


def get_dist_version_string(project, format=" (%s)"):
    return format % project.dist_version if project.version != project.dist_version else ""


def safe_log_file_name(file_name):
    # per https://support.microsoft.com/en-us/kb/177506
    # per https://msdn.microsoft.com/en-us/library/aa365247
    return re.sub(r'\\|/|:|\*|\?|\"|<|>|\|', '_', file_name)


_installed_tblib = False
_mp_billiard_plugin_dir = None


def patch_mp_plugin_dir(plugin_dir):
    global _mp_billiard_plugin_dir

    if not _mp_billiard_plugin_dir:
        _mp_billiard_plugin_dir = plugin_dir


def _install_tblib():
    global _installed_tblib

    if not _installed_tblib:
        from pybuilder._vendor.tblib import pickling_support

        pickling_support.install()
        _installed_tblib = True


def _patched_billiard_spawnv_passfds(path, args, passfds):
    """This is Python 2 only"""
    global _mp_billiard_plugin_dir

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


def _patch_billiard_spawn_passfds():
    """This is Python 2 only"""
    global _old_billiard_spawn_passfds

    if not _old_billiard_spawn_passfds:
        from billiard import compat

        if sys.platform == "win32":
            from billiard import popen_spawn_win32 as popen_spawn
        else:
            from billiard import popen_spawn_posix as popen_spawn

        _old_billiard_spawn_passfds = compat.spawnv_passfds
        compat.spawnv_passfds = _patched_billiard_spawnv_passfds
        popen_spawn.spawnv_passfds = _patched_billiard_spawnv_passfds


def patch_mp():
    _install_tblib()

    if sys.version_info[0] < 3 and sys.platform != "win32":
        from billiard import get_context

        global _mp_get_context
        _mp_get_context = get_context

        _patch_billiard_spawn_passfds()


def mp_get_context(context):
    return _mp_get_context(context)


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


def create_venv(home_dir,
                system_site_packages=False,
                clear=False,
                symlinks=False,
                upgrade=False,
                with_pip=False,
                prompt=None):
    if clear:
        if os.path.exists(home_dir):
            rmtree(home_dir)

    with virtualenv.virtualenv_support_dirs() as search_dirs:
        virtualenv.create_environment(
            home_dir,
            site_packages=system_site_packages,
            prompt=prompt,
            search_dirs=search_dirs,
            download=upgrade,
            no_setuptools=False,
            no_pip=not with_pip,
            no_wheel=False,
            symlink=symlinks,
        )
