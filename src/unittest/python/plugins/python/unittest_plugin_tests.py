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

from os.path import normcase as nc
from unittest import TestCase, TextTestRunner

from pybuilder.core import Project
from pybuilder.plugins.python.unittest_plugin import (execute_tests, execute_tests_matching,
                                                      _register_test_and_source_path_and_return_test_dir,
                                                      _instrument_result,
                                                      _create_runner,
                                                      _get_make_result_method_name,
                                                      report_to_ci_server)
from test_utils import Mock, patch

__author__ = 'Michael Gruber'


class PythonPathTests(TestCase):
    def setUp(self):
        self.project = Project(nc('/path/to/project'))
        self.project.set_property('dir_source_unittest_python', 'unittest')
        self.project.set_property('dir_source_main_python', 'src')

    def test_should_register_source_paths(self):
        system_path = [nc('some/python/path')]

        _register_test_and_source_path_and_return_test_dir(self.project, system_path, "unittest")

        self.assertTrue(nc('/path/to/project/unittest') in system_path)
        self.assertTrue(nc('/path/to/project/src') in system_path)

    def test_should_put_project_sources_before_other_sources(self):
        system_path = [nc('irrelevant/sources')]

        _register_test_and_source_path_and_return_test_dir(self.project, system_path, "unittest")

        test_sources_index_in_path = system_path.index(nc('/path/to/project/unittest'))
        main_sources_index_in_path = system_path.index(nc('/path/to/project/src'))
        irrelevant_sources_index_in_path = system_path.index(nc('irrelevant/sources'))
        self.assertTrue(test_sources_index_in_path < irrelevant_sources_index_in_path and
                        main_sources_index_in_path < irrelevant_sources_index_in_path)


class ExecuteTestsTests(TestCase):
    def setUp(self):
        self.mock_result = Mock()
        self.mock_logger = Mock()

    @patch('unittest.TextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_discover_modules_by_suffix(self, mock_discover_modules_matching, mock_unittest, runner):
        execute_tests(runner, self.mock_logger, '/path/to/test/sources', '_tests.py')

        mock_discover_modules_matching.assert_called_with('/path/to/test/sources', '*_tests.py')

    @patch('unittest.TextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_discover_modules_by_glob(self, mock_discover_modules_matching, mock_unittest, runner):
        execute_tests_matching(runner, self.mock_logger, '/path/to/test/sources', '*_tests.py')

        mock_discover_modules_matching.assert_called_with('/path/to/test/sources', '*_tests.py')

    @patch('unittest.TextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_load_tests_from_discovered_modules(self, mock_discover_modules_matching, mock_unittest, runner):
        mock_modules = Mock()
        mock_discover_modules_matching.return_value = mock_modules

        execute_tests_matching(runner, self.mock_logger, '/path/to/test/sources', '*_tests.py')

        mock_unittest.defaultTestLoader.loadTestsFromNames.assert_called_with(mock_modules)

    @patch('unittest.TextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_run_discovered_and_loaded_tests(self, mock_discover_modules, mock_unittest, runner):
        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests

        execute_tests(runner, self.mock_logger, '/path/to/test/sources', '_tests.py')

        runner.return_value.run.assert_called_with(mock_tests)

    @patch('unittest.TextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_return_actual_test_results(self, mock_discover_modules, mock_unittest, runner):
        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        runner.return_value.run.return_value = self.mock_result

        actual, _ = execute_tests(runner, self.mock_logger, '/path/to/test/sources', '_tests.py')

        self.assertEqual(self.mock_result, actual)

    @patch('unittest.TextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_set_test_method_prefix_when_given(self, mock_discover_modules, mock_unittest, runner):
        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        runner.return_value.run.return_value = self.mock_result

        actual, _ = execute_tests(runner, self.mock_logger, '/path/to/test/sources', '_tests.py',
                                  test_method_prefix='should_')

        self.assertEqual('should_', mock_unittest.defaultTestLoader.testMethodPrefix)


class CIServerInteractionTests(TestCase):
    @patch('pybuilder.ci_server_interaction.TestProxy')
    @patch('pybuilder.ci_server_interaction._is_running_on_teamcity')
    def test_should_report_passed_tests_to_ci_server(self, teamcity, proxy):
        teamcity.return_value = False
        project = Project('basedir')
        mock_proxy = Mock()
        proxy.return_value = mock_proxy
        mock_proxy.and_test_name.return_value = mock_proxy
        mock_proxy.__enter__ = Mock(return_value=mock_proxy)
        mock_proxy.__exit__ = Mock(return_value=False)
        result = Mock()
        result.test_names = ['test1', 'test2', 'test3']
        result.failed_test_names_and_reasons = {}

        report_to_ci_server(project, result)

        mock_proxy.fails.assert_not_called()

    @patch('pybuilder.ci_server_interaction.TestProxy')
    @patch('pybuilder.ci_server_interaction._is_running_on_teamcity')
    def test_should_report_failed_tests_to_ci_server(self, teamcity, proxy):
        teamcity.return_value = False
        project = Project('basedir')
        mock_proxy = Mock()
        proxy.return_value = mock_proxy
        mock_proxy.and_test_name.return_value = mock_proxy
        mock_proxy.__enter__ = Mock(return_value=mock_proxy)
        mock_proxy.__exit__ = Mock(return_value=False)
        result = Mock()
        result.test_names = ['test1', 'test2', 'test3']
        result.failed_test_names_and_reasons = {
            'test2': 'Something went very wrong'
        }

        report_to_ci_server(project, result)

        mock_proxy.fails.assert_called_with('Something went very wrong')


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
            {'test_with_failure': 'type: exception'})

    def test_should_save_exception_details_when_test_error_occurs(self):
        self.mock_test_result.addError(
            "test_with_failure",
            ("type", "exception", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {'test_with_failure': 'type: exception'})

    def test_should_save_exception_details_when_test_failure_with_unicode_occurs(self):
        self.mock_test_result.addFailure(
            "test_with_failure",
            ("type", "exception with ünicode", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {'test_with_failure': 'type: exception with ünicode'})

    def test_should_save_exception_details_when_test_error_with_unicode_occurs(self):
        self.mock_test_result.addError(
            "test_with_failure",
            ("type", "exception with ünicode", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {'test_with_failure': 'type: exception with ünicode'})


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
