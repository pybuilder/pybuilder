#  This file is part of Python Builder
#
#  Copyright 2011 The Python Builder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

__author__ = "Alexander Metzner"

import sys

from pyfix.testcollector import TestCollector
from pyfix.testrunner import TestRunner, TestRunListener

from pythonbuilder.core import init, task, description, use_plugin
from pythonbuilder.errors import BuildFailedException
from pythonbuilder.utils import discover_modules, render_report

use_plugin("python.core")

@init
def init_test_source_directory(project):
    project.set_property_if_unset("dir_source_unittest_python", "src/unittest/python")
    project.set_property_if_unset("pyfix_unittest_file_suffix", "_pyfix_tests.py")


@task
@description("Runs unit tests written using the pyfix test framework")
def run_unit_tests(project, logger):
    sys.path.append(project.expand_path("$dir_source_main_python"))
    test_dir = project.expand_path("$dir_source_unittest_python")
    sys.path.append(test_dir)

    suffix = project.expand("$pyfix_unittest_file_suffix")

    logger.info("Executing pyfix unittests in %s", test_dir)
    logger.debug("Including files ending with '%s'", suffix)

    try:
        result = execute_tests(logger, test_dir, suffix)
        if result.number_of_tests_executed == 0:
            logger.warn("No unittests executed")
        else:
            logger.info("Executed %d pyfix unittests", result.number_of_tests_executed)

        write_report(project, result)

        if not result.success:
            raise BuildFailedException("%d pyfix unittests failed", result.number_of_failures)

        logger.info("All pyfix unittests passed")
    except ImportError as e:
        logger.error("Error importing pyfix unittest: %s", e)
        raise BuildFailedException("Unable to execute unit tests.")


class TestListener(TestRunListener):
    def __init__(self, logger):
        self._logger = logger

    def before_suite(self, test_definitions):
        self._logger.info("Running %d pyfix tests", len(test_definitions))

    def before_test(self, test_definition):
        self._logger.debug("Running pyfix test '%s'", test_definition.name)

    def after_test(self, test_results):
        for test_result in test_results:
            if not test_result.success:
                self._logger.warn("Test '%s' failed: %s", test_result.test_definition.name, test_result.message)


def import_modules(test_modules):
    return [__import__(module_name) for module_name in test_modules]


def execute_tests(logger, test_source, suffix):
    test_module_names = discover_modules(test_source, suffix)
    test_modules = import_modules(test_module_names)

    test_collector = TestCollector()

    for test_module in test_modules:
        test_collector.collect_tests(test_module)

    test_runner = TestRunner()
    test_runner.add_test_run_listener(TestListener(logger))
    return test_runner.run_tests(test_collector.test_suite)


def write_report(project, test_results):
    report = {"tests-run": test_results.number_of_tests_executed,
              "time_in_millis": test_results.execution_time,
              "failures": []}
    for test_result in test_results.test_results:
        if test_result.success:
            continue
        report["failures"].append({"test": test_result.test_definition.name, "message": test_result.message})

    project.write_report("pyfix_unittest.json", render_report(report))