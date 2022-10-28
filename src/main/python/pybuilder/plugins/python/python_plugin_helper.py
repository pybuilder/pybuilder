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

import itertools
import os

from pybuilder.utils import (discover_modules,
                             discover_files_matching,
                             as_list,
                             read_file)


def log_report(logger, name, report_lines):
    count_of_warnings = len(report_lines)
    if count_of_warnings > 0:
        for report_line in report_lines:
            logger.warn(name + ': ' + report_line[:-1])


def discover_python_files(directory, exclude_glob=None):
    return discover_files_matching(directory, "*.py", exclude_glob)


def discover_affected_files(include_test_sources, include_scripts, project):
    source_dir = project.expand_path("$dir_source_main_python")
    files = discover_python_files(source_dir)

    if include_test_sources:
        if project.get_property("dir_source_unittest_python"):
            unittest_dir = project.expand_path("$dir_source_unittest_python")
            files = itertools.chain(files, discover_python_files(unittest_dir))
        if project.get_property("dir_source_integrationtest_python"):
            integrationtest_dir = project.expand_path("$dir_source_integrationtest_python")
            files = itertools.chain(files, discover_python_files(integrationtest_dir))

    if include_scripts and project.get_property("dir_source_main_scripts"):
        scripts_dir = project.expand_path("$dir_source_main_scripts")
        files = itertools.chain(files,
                                discover_files_matching(scripts_dir, "*"))  # we have no idea how scripts might look

    return files


def discover_affected_dirs(include_test_sources, include_scripts, project):
    files = [project.expand_path("$dir_source_main_python")]
    if include_test_sources:
        if _if_property_set_and_dir_exists(project.get_property("dir_source_unittest_python")):
            files.append(project.expand_path("$dir_source_unittest_python"))
        if _if_property_set_and_dir_exists(project.get_property("dir_source_integrationtest_python")):
            files.append(project.expand_path("$dir_source_integrationtest_python"))

    if include_scripts and _if_property_set_and_dir_exists(project.get_property("dir_source_main_scripts")):
        files.append(project.expand_path("$dir_source_main_scripts"))

    return files


def _if_property_set_and_dir_exists(property_value):
    return property_value and os.path.isdir(property_value)


def execute_tool_on_source_files(project, name, python_env, command_and_arguments, logger=None,
                                 include_test_sources=False, include_scripts=False, include_dirs_only=False):
    if include_dirs_only:
        files = discover_affected_dirs(include_test_sources, include_scripts, project)
    else:
        files = discover_affected_files(include_test_sources, include_scripts, project)

    command = as_list(command_and_arguments) + [f for f in files]

    report_file = project.expand_path("$dir_reports/{0}".format(name))

    execution_result = python_env.execute_command(command, report_file), report_file

    report_file = execution_result[1]
    report_lines = read_file(report_file)

    if logger and project.get_property(name + "_verbose_output"):
        log_report(logger, name, report_lines)

    return execution_result


def execute_tool_on_modules(project, name, python_env, command_and_arguments,
                            extend_pythonpath=True,
                            include_packages=True,
                            include_package_modules=True,
                            include_namespace_modules=True):
    source_dir = project.expand_path("$dir_source_main_python")
    modules = discover_modules(source_dir,
                               include_packages=include_packages,
                               include_package_modules=include_package_modules,
                               include_namespace_modules=include_namespace_modules)
    command = as_list(command_and_arguments) + modules

    report_file = project.expand_path("$dir_reports/%s" % name)

    env = {}
    if extend_pythonpath:
        env["PYTHONPATH"] = source_dir

    return python_env.execute_command(command, report_file, env=env), report_file
