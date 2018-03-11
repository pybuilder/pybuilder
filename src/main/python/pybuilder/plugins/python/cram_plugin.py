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
    Plugin for Cram, a functional testing framework for command line
    applications.

    https://pypi.python.org/pypi/cram
"""

import os

from pybuilder.core import after, task, init, use_plugin, depends, description
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.python_plugin_helper import execute_command
from pybuilder.utils import assert_can_execute, discover_files_matching, read_file

__author__ = 'Valentin Haenel'

use_plugin("python.core")


@init
def initialize_cram_plugin(project):
    project.plugin_depends_on("cram")
    project.set_property_if_unset("dir_source_cmdlinetest", "src/cmdlinetest")
    project.set_property_if_unset("cram_test_file_glob", "*.t")
    project.set_property_if_unset("cram_fail_if_no_tests", True)
    project.set_property_if_unset("cram_run_test_from_target", True)


@after("prepare")
def assert_cram_is_executable(logger):
    """ Asserts that the cram script is executable. """
    logger.debug("Checking if cram is executable.")

    assert_can_execute(command_and_arguments=["cram", "--version"],
                       prerequisite="cram",
                       caller="plugin python.cram")


def _cram_command_for(project):
    command_and_arguments = ["cram", '-E']
    if project.get_property("verbose"):
        command_and_arguments.append('--verbose')
    return command_and_arguments


def _find_files(project):
    cram_dir = project.get_property('dir_source_cmdlinetest')
    cram_test_file_glob = project.get_property("cram_test_file_glob")
    cram_files = discover_files_matching(cram_dir, cram_test_file_glob)
    return cram_files


def _report_file(project):
    return project.expand_path("$dir_reports", "cram.err")


def _prepend_path(env, variable, value):
    env[variable] = value + ":" + env.get(variable, '')


@task
@depends("prepare")
@description("Run Cram command line tests")
def run_cram_tests(project, logger):
    logger.info("Running Cram command line tests")

    cram_tests = list(_find_files(project))
    if not cram_tests or len(cram_tests) == 0:
        if project.get_property("cram_fail_if_no_tests"):
            raise BuildFailedException("No Cram tests found!")
        else:
            return

    command_and_arguments = _cram_command_for(project)
    command_and_arguments.extend(cram_tests)
    report_file = _report_file(project)

    env = os.environ.copy()
    if project.get_property('cram_run_test_from_target'):
        dist_dir = project.expand_path("$dir_dist")
        _prepend_path(env, "PYTHONPATH", dist_dir)
        script_dir_dist = project.get_property('dir_dist_scripts')
        _prepend_path(env, "PATH", os.path.join(dist_dir, script_dir_dist))
    else:
        source_dir = project.expand_path("$dir_source_main_python")
        _prepend_path(env, "PYTHONPATH", source_dir)
        script_dir = project.expand_path('$dir_source_main_scripts')
        _prepend_path(env, "PATH", script_dir)

    return_code = execute_command(command_and_arguments,
                                  report_file,
                                  env=env,
                                  error_file_name=report_file)

    report = read_file(report_file)
    result = report[-1][2:].strip()

    if return_code != 0:
        logger.error("Cram tests failed!")
        if project.get_property("verbose"):
            for line in report:
                logger.error(line.rstrip())
        else:
            logger.error(result)

        logger.error("See: '{0}' for details".format(report_file))
        raise BuildFailedException("Cram tests failed!")

    logger.info("Cram tests were fine")
    logger.info(result)


@task
def run_integration_tests(project, logger):
    run_cram_tests(project, logger)
