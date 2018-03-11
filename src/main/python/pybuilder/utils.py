#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2015 PyBuilder Team
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
import re
import subprocess
import sys
import tempfile
import time
import traceback
from collections import OrderedDict
from multiprocessing import Process
from subprocess import Popen, PIPE

try:
    from multiprocessing import SimpleQueue
except ImportError:
    from multiprocessing.queues import SimpleQueue

try:
    basestring = basestring
except NameError:
    basestring = str

from pybuilder.errors import MissingPrerequisiteException, PyBuilderException

if sys.version_info[0] < 3:  # if major is less than 3
    from .excp_util_2 import raise_exception, is_string

    is_string = is_string
else:
    from .excp_util_3 import raise_exception, is_string

    is_string = is_string

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


def discover_files_matching(start_dir, file_glob):
    for root, _, files in os.walk(start_dir):
        for file_name in files:
            if fnmatch.fnmatch(file_name, file_glob):
                yield os.path.join(root, file_name)


def execute_command(command_and_arguments, outfile_name=None, env=None, cwd=None, error_file_name=None, shell=False):
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
        import tailer
    except ImportError:
        return read_file(file_path)

    with open(file_path) as f:
        return tailer.tail(f, lines)


def tail_log(file_path, lines=20):
    return "\n".join("\t" + l for l in tail(file_path, lines))


def assert_can_execute(command_and_arguments, prerequisite, caller):
    with tempfile.NamedTemporaryFile() as f:
        try:
            process = subprocess.Popen(command_and_arguments, stdout=f, stderr=f, shell=False)
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
    os.makedirs(directory)


def is_windows():
    return any(win_platform in sys.platform for win_platform in ("win32", "cygwin", "msys"))


def fake_windows_fork(group, target, name, args, kwargs):
    return 0, target(*args, **kwargs)


def fork_process(logger, group=None, target=None, name=None, args=(), kwargs={}):
    """
    Forks a child, making sure that all exceptions from the child are safely sent to the parent
    If a target raises an exception, the exception is re-raised in the parent process
    @return tuple consisting of process exit code and target's return value
    """
    if is_windows():
        logger.warn(
            "Not forking for %s due to Windows incompatibilities (see #184). "
            "Measurements (coverage, etc.) might be biased." % target)
        return fake_windows_fork(group, target, name, args, kwargs)
    try:
        sys.modules["tblib.pickling_support"]
    except KeyError:
        import tblib.pickling_support

        tblib.pickling_support.install()

    q = SimpleQueue()

    def instrumented_target(*args, **kwargs):
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

    p = Process(group=group, target=instrumented_target, name=name, args=args, kwargs=kwargs)
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
