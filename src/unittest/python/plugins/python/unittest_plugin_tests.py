#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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

__author__ = 'Michael Gruber'

from unittest import TestCase

from mock import Mock, patch
from pybuilder.plugins.python.unittest_plugin import execute_tests


class ExecuteTestsTests(TestCase):

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules')
    def test_should_discover_modules_in_given_path(self, mock_discover_modules, mock_unittest):

        execute_tests('/path/to/test/sources', '_tests.py')

        mock_discover_modules.assert_called_with('/path/to/test/sources', '_tests.py')

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules')
    def test_should_load_tests_from_discovered_modules(self, mock_discover_modules, mock_unittest):

        mock_modules = Mock()
        mock_discover_modules.return_value = mock_modules

        execute_tests('/path/to/test/sources', '_tests.py')

        mock_unittest.defaultTestLoader.loadTestsFromNames.assert_called_with(mock_modules)

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules')
    def test_should_run_discovered_and_loaded_tests(self, mock_discover_modules, mock_unittest):

        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        mock_test_runner = Mock()
        mock_unittest.TextTestRunner.return_value = mock_test_runner

        execute_tests('/path/to/test/sources', '_tests.py')

        mock_test_runner.run.assert_called_with(mock_tests)

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules')
    def test_should_return_actual_test_results(self, mock_discover_modules, mock_unittest):

        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        mock_test_runner = Mock()
        mock_result = Mock()
        mock_test_runner.run.return_value = mock_result
        mock_unittest.TextTestRunner.return_value = mock_test_runner

        actual, _ = execute_tests('/path/to/test/sources', '_tests.py')

        self.assertEqual(mock_result, actual)

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules')
    def test_should_set_test_method_prefix_when_given(self, mock_discover_modules, mock_unittest):

        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        mock_test_runner = Mock()
        mock_result = Mock()
        mock_test_runner.run.return_value = mock_result
        mock_unittest.TextTestRunner.return_value = mock_test_runner

        actual, _ = execute_tests('/path/to/test/sources', '_tests.py', test_method_prefix='should_')

        self.assertEqual('should_', mock_unittest.defaultTestLoader.testMethodPrefix)
