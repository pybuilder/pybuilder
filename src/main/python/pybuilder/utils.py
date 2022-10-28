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

"""
    The PyBuilder utils module.
    Provides generic utilities that can be used by plugins.
"""
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from os.path import normcase, normpath, abspath, realpath, join
from subprocess import Popen, PIPE

from pybuilder.errors import MissingPrerequisiteException, PyBuilderException
from pybuilder.python_utils import (is_string, which, makedirs,
                                    IS_WIN, iglob, escape)

try:
    from collections import abc
except ImportError:
    import collections as abc


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
        return file_name[0:-3]
    return file_name


def discover_module_files(source_path, suffix=".py"):
    return discover_module_files_matching(source_path, "*{0}".format(suffix))


def discover_module_files_matching(source_path, module_glob):
    result = []
    if not module_glob.endswith(".py"):
        module_glob += ".py"
    for module_file_path in discover_files_matching(source_path, module_glob):
        relative_module_file_path = os.path.relpath(module_file_path, source_path)
        module_file = remove_leading_slash_or_dot_from_path(relative_module_file_path)
        result.append(module_file)
    return result


def discover_modules(source_path, suffix=".py",
                     include_packages=True,
                     include_package_modules=True,
                     include_namespace_modules=True
                     ):
    return discover_modules_matching(source_path, "*{0}".format(suffix),
                                     include_packages=include_packages,
                                     include_package_modules=include_package_modules,
                                     include_namespace_modules=include_namespace_modules)


def discover_modules_matching(source_path, module_glob,
                              include_packages=True,
                              include_package_modules=True,
                              include_namespace_modules=True):
    result = []
    if not module_glob.endswith(".py"):
        module_glob += ".py"

    for root, dirs, files in os.walk(source_path, followlinks=True):
        is_package = False
        for file_name in files:
            if file_name == "__init__.py":
                is_package = True
                break

        for file_name in files:
            if fnmatch.fnmatch(file_name, module_glob):
                module_file_path = jp(root, file_name)
                relative_module_file_path = os.path.relpath(module_file_path, source_path)
                relative_module_file_path = relative_module_file_path.replace(os.sep, ".")
                module_file = remove_leading_slash_or_dot_from_path(relative_module_file_path)
                module_name = remove_python_source_suffix(module_file)

                add_module = False
                if file_name == "__init__.py":
                    if include_packages:
                        module_name = module_name[:-9]  # len(".__init__")
                        add_module = True
                else:
                    add_module = (not is_package and include_namespace_modules or
                                  is_package and include_package_modules)

                if add_module:
                    result.append(module_name)
    return result


def discover_files(start_dir, suffix):
    return discover_files_matching(start_dir, "*{0}".format(suffix))


def discover_files_matching(start_dir, file_glob, exclude_file_glob=None):
    for root, _, files in os.walk(start_dir, followlinks=True):
        for file_name in files:
            if exclude_file_glob:
                for exclude_pat in as_list(exclude_file_glob):
                    if fnmatch.fnmatch(file_name, exclude_pat):
                        continue
            if fnmatch.fnmatch(file_name, file_glob):
                yield os.path.join(root, file_name)


def assert_can_execute(command_and_arguments, prerequisite, caller, env, no_path_search=False, logger=None):
    with tempfile.NamedTemporaryFile() as f:
        try:
            if IS_WIN and not is_string(command_and_arguments) and not no_path_search:
                which_cmd = which(command_and_arguments[0], path=env.get("PATH") if env else None)
                if which_cmd:
                    command_and_arguments[0] = which_cmd

            if logger:
                logger.debug("Verifying command: %s", " ".join(repr(cmd) for cmd in command_and_arguments))

            process = subprocess.Popen(command_and_arguments, stdout=f, stderr=f, shell=False, env=env)
            process.wait()
        except OSError:
            raise MissingPrerequisiteException(prerequisite, caller)


def execute_command(command_and_arguments, outfile_name=None, env=None, cwd=None, error_file_name=None, shell=False,
                    no_path_search=False, logger=None):
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
            if not shell and IS_WIN and not is_string(command_and_arguments) and not no_path_search:
                which_cmd = which(command_and_arguments[0], path=env.get("PATH") if env else None)
                if which_cmd:
                    command_and_arguments[0] = which_cmd

            if logger:
                logger.debug("Executing command: %s", " ".join(repr(cmd) for cmd in command_and_arguments))

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
    return "\n".join("\t" + line for line in tail(file_path, lines))


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
    for glob in globs:
        for absolute_file_name in iglob(normcase(os.path.join(escape(start_directory), glob)), recursive=True):
            if os.path.isdir(absolute_file_name):
                continue
            relative_file_name = os.path.relpath(absolute_file_name, start_directory)
            closure(absolute_file_name,
                    relative_file_name,
                    *additional_closure_arguments,
                    **keyword_closure_arguments)


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


def is_notstr_iterable(obj):
    """Checks if obj is iterable, but not a string"""
    return not isinstance(obj, str) and isinstance(obj, abc.Iterable)


def get_dist_version_string(project, format=" (%s)"):
    return format % project.dist_version if project.version != project.dist_version else ""


def safe_log_file_name(file_name):
    # per https://support.microsoft.com/en-us/kb/177506
    # per https://msdn.microsoft.com/en-us/library/aa365247
    return re.sub(r'\\|/|:|\*|\?|\"|<|>|\|', '_', file_name)


nc = normcase
jp = join


def np(path):
    return nc(normpath(path))


def ap(path):
    return nc(abspath(path))


def rp(path):
    return nc(realpath(path))
