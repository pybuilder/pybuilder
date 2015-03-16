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

from __future__ import unicode_literals

from unittest import TestCase

from mock import Mock, patch
from pybuilder.core import Project
from pybuilder.plugins.python.unittest_plugin import TestNameAwareTestResult as TestNameAwareTestResultFromPlugin
from pybuilder.plugins.python.unittest_plugin import (execute_tests, execute_tests_matching,
                                                      _register_test_and_source_path_and_return_test_dir,
                                                      report_to_ci_server)


__author__ = 'Michael Gruber'


class PythonPathTests(TestCase):

    def setUp(self):
        self.project = Project('/path/to/project')
        self.project.set_property('dir_source_unittest_python', 'unittest')
        self.project.set_property('dir_source_main_python', 'src')

    def test_should_register_source_paths(self):
        system_path = ['some/python/path']

        _register_test_and_source_path_and_return_test_dir(self.project, system_path)

        self.assertTrue('/path/to/project/unittest' in system_path)
        self.assertTrue('/path/to/project/src' in system_path)

    def test_should_put_project_sources_before_other_sources(self):
        system_path = ['irrelevant/sources']

        _register_test_and_source_path_and_return_test_dir(self.project, system_path)

        test_sources_index_in_path = system_path.index('/path/to/project/unittest')
        main_sources_index_in_path = system_path.index('/path/to/project/src')
        irrelevant_sources_index_in_path = system_path.index('irrelevant/sources')
        self.assertTrue(test_sources_index_in_path < irrelevant_sources_index_in_path and
                        main_sources_index_in_path < irrelevant_sources_index_in_path)


class ExecuteTestsTests(TestCase):

    def setUp(self):
        self.mock_result = Mock()
        self.mock_logger = Mock()

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_discover_modules_by_suffix(self, mock_discover_modules_matching, mock_unittest, runner):

        execute_tests(self.mock_logger, '/path/to/test/sources', '_tests.py')

        mock_discover_modules_matching.assert_called_with('/path/to/test/sources', '*_tests.py')

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_discover_modules_by_glob(self, mock_discover_modules_matching, mock_unittest, runner):

        execute_tests_matching(self.mock_logger, '/path/to/test/sources', '*_tests.py')

        mock_discover_modules_matching.assert_called_with('/path/to/test/sources', '*_tests.py')

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_load_tests_from_discovered_modules(self, mock_discover_modules_matching, mock_unittest, runner):

        mock_modules = Mock()
        mock_discover_modules_matching.return_value = mock_modules

        execute_tests_matching(self.mock_logger, '/path/to/test/sources', '*_tests.py')

        mock_unittest.defaultTestLoader.loadTestsFromNames.assert_called_with(mock_modules)

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_run_discovered_and_loaded_tests(self, mock_discover_modules, mock_unittest, runner):

        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests

        execute_tests(self.mock_logger, '/path/to/test/sources', '_tests.py')

        runner.return_value.run.assert_called_with(mock_tests)

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_return_actual_test_results(self, mock_discover_modules, mock_unittest, runner):

        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        runner.return_value.run.return_value = self.mock_result

        actual, _ = execute_tests(self.mock_logger, '/path/to/test/sources', '_tests.py')

        self.assertEqual(self.mock_result, actual)

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_set_test_method_prefix_when_given(self, mock_discover_modules, mock_unittest, runner):
        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        runner.return_value.run.return_value = self.mock_result

        actual, _ = execute_tests(self.mock_logger, '/path/to/test/sources', '_tests.py', test_method_prefix='should_')

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

    def setUp(self):
        self.mock_test_result = Mock(TestNameAwareTestResultFromPlugin)
        TestNameAwareTestResultFromPlugin.__init__(self.mock_test_result, Mock(), Mock(), Mock(), Mock())

    def test_should_append_test_name_when_running_test(self):
        TestNameAwareTestResultFromPlugin.startTest(self.mock_test_result, "any_test_name")

        self.assertEqual(self.mock_test_result.test_names, ["any_test_name"])

    def test_should_save_exception_details_when_test_failure_occurs(self):
        TestNameAwareTestResultFromPlugin.addFailure(
            self.mock_test_result,
            "test_with_failure",
            ("type", "exception", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {'test_with_failure': 'type: exception'})

    def test_should_save_exception_details_when_test_error_occurs(self):
        TestNameAwareTestResultFromPlugin.addError(
            self.mock_test_result,
            "test_with_failure",
            ("type", "exception", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {'test_with_failure': 'type: exception'})

    def test_should_save_exception_details_when_test_failure_with_unicode_occurs(self):
        TestNameAwareTestResultFromPlugin.addFailure(
            self.mock_test_result,
            "test_with_failure",
            ("type", "exception with ünicode", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {'test_with_failure': 'type: exception with ünicode'})

    def test_should_save_exception_details_when_test_error_with_unicode_occurs(self):
        TestNameAwareTestResultFromPlugin.addError(
            self.mock_test_result,
            "test_with_failure",
            ("type", "exception with ünicode", "traceback"))

        self.assertEqual(
            self.mock_test_result.failed_test_names_and_reasons,
            {'test_with_failure': 'type: exception with ünicode'})
