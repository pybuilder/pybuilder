#   -*- coding: utf-8 -*-
#
#   Copyright 2016 Alexey Sanko
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

from sys import path as sys_path

from pybuilder.core import task, init, use_plugin, after
from pybuilder.errors import MissingPrerequisiteException, BuildFailedException
from pybuilder.utils import register_test_and_source_path_and_return_test_dir

__author__ = 'Alexey Sanko'

use_plugin("python.core")


@init
def initialize_pytest_plugin(project):
    """ Init default plugin project properties. """
    project.plugin_depends_on('pytest')
    project.set_property_if_unset("dir_source_pytest_python", "src/unittest/python")
    project.set_property_if_unset("pytest_report_file", "target/reports/junit.xml")
    project.set_property_if_unset("pytest_extra_args", [])


@after("prepare")
def assert_pytest_available(logger):
    """ Asserts that the pytest module is available. """
    logger.debug("Checking if pytest module is available.")

    try:
        import pytest
        logger.debug("Found pytest version %s" % pytest.__version__)
    except ImportError:
        raise MissingPrerequisiteException(prerequisite="pytest module", caller="plugin python.pytest")


@task
def run_unit_tests(project, logger):
    """ Call pytest for the sources of the given project. """
    logger.info('pytest: Run unittests.')
    from pytest import main as pytest_main
    test_dir = register_test_and_source_path_and_return_test_dir(project, sys_path, 'pytest')
    extra_args = project.get_property("pytest_extra_args")
    try:
        pytest_args = [test_dir]
        if project.get_property('verbose'):
            pytest_args.append('-s')
            pytest_args.append('-v')
        pytest_args.append('--junit-xml')
        pytest_args.append(project.expand_path('$pytest_report_file'))
        pytest_args = pytest_args + (extra_args if extra_args else [])
        ret = pytest_main(pytest_args)
        if ret:
            raise BuildFailedException('pytest: unittests failed')
        else:
            logger.info('pytest: All unittests passed.')
    except:
        raise
