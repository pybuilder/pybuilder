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

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO

import sys
import unittest

from pybuilder.core import init, task, description, use_plugin
from pybuilder.errors import BuildFailedException
from pybuilder.utils import discover_modules_matching, render_report
from pybuilder.ci_server_interaction import test_proxy_for
from pybuilder.terminal import print_text_line
use_plugin("python.core")

if sys.version_info < (2, 7):
    TextTestResult = unittest._TextTestResult  # brought to you by 2.6
else:
    TextTestResult = unittest.TextTestResult


class TestNameAwareTextTestRunner(unittest.TextTestRunner):

    def __init__(self, logger, stream):
        self.logger = logger
        super(TestNameAwareTextTestRunner, self).__init__(stream=stream)

    def _makeResult(self):
        return TestNameAwareTestResult(self.logger, self.stream, self.descriptions, self.verbosity)


class TestNameAwareTestResult(TextTestResult):

    def __init__(self, logger, stream, descriptions, verbosity):
        self.test_names = []
        self.failed_test_names_and_reasons = {}
        self.logger = logger
        super(TestNameAwareTestResult, self).__init__(stream, descriptions, verbosity)

    def startTest(self, test):
        self.test_names.append(test)
        self.logger.debug("starting %s", test)
        super(TestNameAwareTestResult, self).startTest(test)

    def addError(self, test, err):
        exception_type, exception, traceback = err
        self.failed_test_names_and_reasons[test] = '{0}: {1}'.format(exception_type, exception).replace('\'', '')
        super(TestNameAwareTestResult, self).addError(test, err)

    def addFailure(self, test, err):
        exception_type, exception, traceback = err
        self.failed_test_names_and_reasons[test] = '{0}: {1}'.format(exception_type, exception).replace('\'', '')
        super(TestNameAwareTestResult, self).addFailure(test, err)


@init
def init_test_source_directory(project):
    project.set_property_if_unset("dir_source_unittest_python", "src/unittest/python")
    project.set_property_if_unset("unittest_module_glob", "*_tests")
    project.set_property_if_unset("unittest_file_suffix", None)  # deprecated, use unittest_module_glob.
    project.set_property_if_unset("unittest_test_method_prefix", None)


@task
@description("Runs unit tests based on Python's unittest module")
def run_unit_tests(project, logger):
    test_dir = _register_test_and_source_path_and_return_test_dir(project, sys.path)

    unittest_file_suffix = project.get_property("unittest_file_suffix")
    if unittest_file_suffix is not None:
        logger.warn("unittest_file_suffix is deprecated, please use unittest_module_glob")
        module_glob = "*{0}".format(unittest_file_suffix)
        if module_glob.endswith(".py"):
            WITHOUT_DOT_PY = slice(0, -3)
            module_glob = module_glob[WITHOUT_DOT_PY]
        project.set_property("unittest_module_glob", module_glob)
    else:
        module_glob = project.get_property("unittest_module_glob")

    logger.info("Executing unittest Python modules in %s", test_dir)
    logger.debug("Including files matching '%s'", module_glob)

    try:
        test_method_prefix = project.get_property("unittest_test_method_prefix")
        result, console_out = execute_tests_matching(logger, test_dir, module_glob, test_method_prefix)

        if result.testsRun == 0:
            logger.warn("No unittests executed.")
        else:
            logger.info("Executed %d unittests", result.testsRun)

        write_report("unittest", project, logger, result, console_out)

        if not result.wasSuccessful():
            raise BuildFailedException("There were %d test error(s) and %d failure(s)"
                                       % (len(result.errors), len(result.failures)))
        logger.info("All unittests passed.")
    except ImportError as e:
        import traceback
        _, _, import_error_traceback = sys.exc_info()
        file_with_error, error_line, _, statement_causing_error = traceback.extract_tb(import_error_traceback)[-1]
        logger.error("Import error in unittest file {0}, due to statement '{1}' on line {2}".format(
            file_with_error, statement_causing_error, error_line))
        logger.error("Error importing unittests: %s", e)
        raise BuildFailedException("Unable to execute unit tests.")


def execute_tests(logger, test_source, suffix, test_method_prefix=None):
    return execute_tests_matching(logger, test_source, "*{0}".format(suffix), test_method_prefix)


def execute_tests_matching(logger, test_source, file_glob, test_method_prefix=None):
    output_log_file = StringIO()

    try:
        test_modules = discover_modules_matching(test_source, file_glob)
        loader = unittest.defaultTestLoader
        if test_method_prefix:
            loader.testMethodPrefix = test_method_prefix
        tests = loader.loadTestsFromNames(test_modules)
        result = TestNameAwareTextTestRunner(logger, output_log_file).run(tests)
        return result, output_log_file.getvalue()
    finally:
        output_log_file.close()


def _register_test_and_source_path_and_return_test_dir(project, system_path):
    test_dir = project.expand_path("$dir_source_unittest_python")
    system_path.insert(0, test_dir)
    system_path.insert(0, project.expand_path("$dir_source_main_python"))

    return test_dir


def write_report(name, project, logger, result, console_out):
    project.write_report("%s" % name, console_out)

    report = {"tests-run": result.testsRun,
              "errors": [],
              "failures": []}

    for error in result.errors:
        report["errors"].append({"test": error[0].id(),
                                 "traceback": error[1]})
        logger.error("Test has error: %s", error[0].id())

        if project.get_property("verbose"):
            print_text_line(error[1])

    for failure in result.failures:
        report["failures"].append({"test": failure[0].id(),
                                   "traceback": failure[1]})
        logger.error("Test failed: %s", failure[0].id())

        if project.get_property("verbose"):
            print_text_line(failure[1])

    project.write_report("%s.json" % name, render_report(report))

    report_to_ci_server(project, result)


def report_to_ci_server(project, result):
    for test_name in result.test_names:
        with test_proxy_for(project).and_test_name(test_name) as test:
            if test_name in result.failed_test_names_and_reasons:
                test.fails(result.failed_test_names_and_reasons.get(test_name))
