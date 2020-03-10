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
    Plugin for Cram, a functional testing framework for command line
    applications.

    https://pypi.python.org/pypi/cram
"""

import os

from pybuilder.core import after, task, init, use_plugin, depends, description, before
from pybuilder.errors import BuildFailedException
from pybuilder.utils import discover_files_matching, read_file, tail_log

__author__ = 'Valentin Haenel'

use_plugin("python.core")


@init
def initialize_cram_plugin(project):
    project.plugin_depends_on("cram")

    project.set_property_if_unset("dir_source_cmdlinetest", "src/cmdlinetest")
    project.set_property_if_unset("cram_test_file_glob", "*.t")
    project.set_property_if_unset("cram_fail_if_no_tests", True)
    project.set_property_if_unset("cram_run_test_from_target", True)


@before("prepare")
def coverage_init(project, logger, reactor):
    em = reactor.execution_manager

    if em.is_task_in_current_execution_plan("coverage") and em.is_task_in_current_execution_plan(
            "run_integration_tests"):
        project.get_property("_coverage_tasks").append(run_integration_tests)
        project.get_property("_coverage_config_prefixes")[run_integration_tests] = "cram"
        project.set_property("cram_coverage_name", "Python Cram test")
        project.set_property("cram_coverage_python_env", "pybuilder")


@after("prepare")
def assert_cram_is_executable(project, logger, reactor):
    """ Asserts that the cram script is executable. """
    logger.debug("Checking if cram is executable.")

    reactor.pybuilder_venv.verify_can_execute(
        command_and_arguments=reactor.pybuilder_venv.executable + ["-m", "cram", "--version"],
        prerequisite="cram", caller="plugin python.cram")


def _cram_command_for(project):
    command_and_arguments = ["-m", "cram", '-E']
    if project.get_property("verbose"):
        command_and_arguments.append("--verbose")
    return command_and_arguments


def _find_files(project):
    cram_dir = project.get_property("dir_source_cmdlinetest")
    cram_test_file_glob = project.get_property("cram_test_file_glob")
    cram_files = discover_files_matching(cram_dir, cram_test_file_glob)
    return cram_files


def _report_file(project):
    return project.expand_path("$dir_reports", "cram.err")


def _prepend_path(env, variable, value):
    env[variable] = value + os.pathsep + env.get(variable, '')


@task
@depends("prepare")
@description("Run Cram command line tests")
def run_cram_tests(project, logger, reactor):
    logger.info("Running Cram command line tests")

    cram_tests = list(_find_files(project))
    if not cram_tests or len(cram_tests) == 0:
        if project.get_property("cram_fail_if_no_tests"):
            raise BuildFailedException("No Cram tests found!")
        else:
            return

    pyb_venv = reactor.pybuilder_venv

    command_and_arguments = pyb_venv.executable + _cram_command_for(project)
    command_and_arguments.extend(cram_tests)
    report_file = _report_file(project)

    pyb_environ = pyb_venv.environ
    if project.get_property("cram_run_test_from_target"):
        dist_dir = project.expand_path("$dir_dist")
        _prepend_path(pyb_environ, "PYTHONPATH", dist_dir)
        script_dir_dist = project.get_property("dir_dist_scripts")
        _prepend_path(pyb_environ, "PATH", os.path.join(dist_dir, script_dir_dist))
    else:
        source_dir = project.expand_path("$dir_source_main_python")
        _prepend_path(pyb_environ, "PYTHONPATH", source_dir)
        script_dir = project.expand_path("$dir_source_main_scripts")
        _prepend_path(pyb_environ, "PATH", script_dir)

    return_code = pyb_venv.execute_command(command_and_arguments,
                                           report_file,
                                           env=pyb_environ,
                                           error_file_name=report_file)

    if return_code != 0:
        error_str = "Cram tests failed! See %s for full details:\n%s" % (report_file, tail_log(report_file))
        logger.error(error_str)
        raise BuildFailedException(error_str)

    report = read_file(report_file)
    result = report[-1][2:].strip()
    logger.info("Cram tests were fine")
    logger.info(result)


@task
def run_integration_tests(project, logger, reactor):
    run_cram_tests(project, logger, reactor)
