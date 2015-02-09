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

import sys

from pyfix.testcollector import TestCollector
from pyfix.testrunner import TestRunner, TestRunListener

from pybuilder.errors import BuildFailedException
from pybuilder.utils import discover_modules_matching, render_report


__author__ = "Alexander Metzner"


def run_unit_tests(project, logger):
    sys.path.append(project.expand_path("$dir_source_main_python"))
    test_dir = project.expand_path("$dir_source_unittest_python")
    sys.path.append(test_dir)

    pyfix_unittest_file_suffix = project.get_property("pyfix_unittest_file_suffix")
    if pyfix_unittest_file_suffix is not None:
        logger.warn("pyfix_unittest_file_suffix is deprecated, please use pyfix_unittest_module_glob")
        module_glob = "*{0}".format(pyfix_unittest_file_suffix)
        if module_glob.endswith(".py"):
            module_glob = module_glob[:-3]
        project.set_property("pyfix_unittest_module_glob", module_glob)
    else:
        module_glob = project.get_property("pyfix_unittest_module_glob")

    logger.info("Executing pyfix unittest Python modules in %s", test_dir)
    logger.debug("Including files matching '%s.py'", module_glob)

    try:
        result = execute_tests_matching(logger, test_dir, module_glob)
        if result.number_of_tests_executed == 0:
            logger.warn("No pyfix executed")
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
    return execute_tests_matching(logger, test_source, "*{0}".format(suffix))


def execute_tests_matching(logger, test_source, module_glob):
    test_module_names = discover_modules_matching(test_source, module_glob)
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
        report["failures"].append({"test": test_result.test_definition.name, "message": test_result.message,
                                   "traceback": test_result.traceback_as_string})

    project.write_report("pyfix_unittest.json", render_report(report))
