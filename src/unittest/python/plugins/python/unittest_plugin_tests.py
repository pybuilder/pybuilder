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

from __future__ import unicode_literals

from unittest import TestCase, TextTestRunner

from pybuilder.core import Project
from pybuilder.plugins.python.unittest_plugin import (execute_tests, execute_tests_matching,
                                                      _instrument_result,
                                                      _create_runner,
                                                      _get_make_result_method_name,
                                                      report_to_ci_server)
from pybuilder.utils import np
from test_utils import Mock, patch

__author__ = "Michael Gruber"


class PythonPathTests(TestCase):
    def setUp(self):
        self.project = Project(np("/path/to/project"))
        self.project.set_property("dir_source_unittest_python", "unittest")
        self.project.set_property("dir_source_main_python", "src")


class ExecuteTestsTests(TestCase):
    def setUp(self):
        self.mock_result = Mock()
        self.mock_logger = Mock()

    @patch("pybuilder.plugins.python.unittest_plugin.start_unittest_tool")
    @patch("unittest.TextTestRunner")
    @patch("pybuilder.plugins.python.unittest_plugin.unittest")
    @patch("pybuilder.plugins.python.unittest_plugin.discover_modules_matching")
    def test_should_discover_modules_by_suffix(self, mock_discover_modules_matching, mock_unittest, runner, tool):
        pipe = Mock()
        pipe.remote_close_cause.return_value = None
        tool.return_value = (Mock(), pipe)
        execute_tests(Mock(), [], runner, self.mock_logger, "/path/to/test/sources", "_tests.py", ["a", "b"])

        mock_discover_modules_matching.assert_called_with("/path/to/test/sources", "*_tests.py")

    @patch("pybuilder.plugins.python.unittest_plugin.start_unittest_tool")
    @patch("unittest.TextTestRunner")
    @patch("pybuilder.plugins.python.unittest_plugin.unittest")
    @patch("pybuilder.plugins.python.unittest_plugin.discover_modules_matching")
    def test_should_discover_modules_by_glob(self, mock_discover_modules_matching, mock_unittest, runner, tool):
        pipe = Mock()
        pipe.remote_close_cause.return_value = None
        tool.return_value = (Mock(), pipe)
        execute_tests_matching(Mock(), [], runner, self.mock_logger, "/path/to/test/sources", "*_tests.py", ["a", "b"])

        mock_discover_modules_matching.assert_called_with("/path/to/test/sources", "*_tests.py")

    @patch("pybuilder.plugins.python.unittest_plugin.start_unittest_tool")
    @patch("unittest.TextTestRunner")
    @patch("pybuilder.plugins.python.unittest_plugin.unittest")
    @patch("pybuilder.utils.discover_modules")
    def test_should_return_actual_test_results(self, mock_discover_modules, mock_unittest, runner, tool):
        pipe = Mock()
        pipe.remote_close_cause.return_value = None
        tool.return_value = (Mock(), pipe)
        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        runner.return_value.run.return_value = self.mock_result

        actual, _ = execute_tests(Mock(), [], runner, self.mock_logger, "/path/to/test/sources", "_tests.py",
                                  ["a", "b"])

        self.assertEqual(self.mock_result, actual)


class CIServerInteractionTests(TestCase):
    @patch("pybuilder.ci_server_interaction.TestProxy")
    @patch("pybuilder.ci_server_interaction._is_running_on_teamcity")
    def test_should_report_passed_tests_to_ci_server(self, teamcity, proxy):
        teamcity.return_value = False
        project = Project("basedir")
        mock_proxy = Mock()
        proxy.return_value = mock_proxy
        mock_proxy.and_test_name.return_value = mock_proxy
        mock_proxy.__enter__ = Mock(return_value=mock_proxy)
        mock_proxy.__exit__ = Mock(return_value=False)
        result = Mock()
        result.test_names = ["test1", "test2", "test3"]
        result.failed_test_names_and_reasons = {}

        report_to_ci_server(project, result)

        mock_proxy.fails.assert_not_called()

    @patch("pybuilder.ci_server_interaction.TestProxy")
    @patch("pybuilder.ci_server_interaction._is_running_on_teamcity")
    def test_should_report_failed_tests_to_ci_server(self, teamcity, proxy):
        teamcity.return_value = False
        project = Project("basedir")
        mock_proxy = Mock()
        proxy.return_value = mock_proxy
        mock_proxy.and_test_name.return_value = mock_proxy
        mock_proxy.__enter__ = Mock(return_value=mock_proxy)
        mock_proxy.__exit__ = Mock(return_value=False)
        result = Mock()
        result.test_names = ["test1", "test2", "test3"]
        result.failed_test_names_and_reasons = {
            "test2": "Something went very wrong"
        }

        report_to_ci_server(project, result)

        mock_proxy.fails.assert_called_with("Something went very wrong")


class TestNameAwareTestResult(TestCase):
    class TestResult(object):
        def __init__(self):
            pass

        def startTest(self, test):
            pass

        def addError(self, test, err):
            pass

        def addFailure(self, test, err):
            pass

    def setUp(self):
        self.mock_test_result = _instrument_result(Mock(), TestNameAwareTestResult.TestResult())

    def test_should_append_test_name_when_running_test(self):
        self.mock_test_result.startTest("any_test_name")

        self.assertEqual(self.mock_test_result.test_names, ["any_test_name"])

    def test_should_save_exception_details_when_test_failure_occurs(self):
        self.mock_test_result.addFailure(
            "test_with_failure",
            ("type", "exception", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {"test_with_failure": "type: exception"})

    def test_should_save_exception_details_when_test_error_occurs(self):
        self.mock_test_result.addError(
            "test_with_failure",
            ("type", "exception", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {"test_with_failure": "type: exception"})

    def test_should_save_exception_details_when_test_failure_with_unicode_occurs(self):
        self.mock_test_result.addFailure(
            "test_with_failure",
            ("type", "exception with ünicode", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {"test_with_failure": "type: exception with ünicode"})

    def test_should_save_exception_details_when_test_error_with_unicode_occurs(self):
        self.mock_test_result.addError(
            "test_with_failure",
            ("type", "exception with ünicode", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {"test_with_failure": "type: exception with ünicode"})


class UnittestRunnerTest(TestCase):
    def test_create_runner_from_class(self):
        self.assertTrue(isinstance(_create_runner(TextTestRunner), TextTestRunner))

    def test_create_runner_from_str(self):
        self.assertTrue(isinstance(_create_runner("unittest.TextTestRunner"), TextTestRunner))

    def test_create_runner_from_tuple_class(self):
        self.assertTrue(isinstance(_create_runner((TextTestRunner, Mock())), TextTestRunner))

    def test_create_runner_from_tuple_str(self):
        self.assertTrue(isinstance(_create_runner(("unittest.TextTestRunner", Mock())), TextTestRunner))

    def test_get_make_result_method_name_default(self):
        self.assertEqual(_get_make_result_method_name(TextTestRunner), "_makeResult")

    def test_get_make_result_method_name_from_str(self):
        self.assertEqual(_get_make_result_method_name((TextTestRunner, "_makeResult")), "_makeResult")

    def test_get_make_result_method_name_from_method(self):
        self.assertEqual(_get_make_result_method_name((TextTestRunner, TextTestRunner._makeResult)), "_makeResult")

    def test_get_make_result_method_name_from_func(self):
        def _makeResult(self):
            pass

        self.assertEqual(_get_make_result_method_name((TextTestRunner, _makeResult)), "_makeResult")


class UnittestRunnerCompatibilityTest(TestCase):
    def test_sub_tests_issue_735(self):
        """
        Test that numbers between 0 and 5 are all between 0 and 5.
        """

        for i in range(0, 6):
            with self.subTest(i=i):
                self.assertLess(i, 6)
                self.assertGreaterEqual(i, 0)
