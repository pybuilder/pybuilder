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
from pybuilder.core import Project
from pybuilder.plugins.python.unittest_plugin import (execute_tests, execute_tests_matching,
                                                      _register_test_and_source_path_and_return_test_dir)


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

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_discover_modules_by_suffix(self, mock_discover_modules_matching, mock_unittest):

        execute_tests('/path/to/test/sources', '_tests.py')

        mock_discover_modules_matching.assert_called_with('/path/to/test/sources', '*_tests.py')

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_discover_modules_by_glob(self, mock_discover_modules_matching, mock_unittest):

        execute_tests_matching('/path/to/test/sources', '*_tests.py')

        mock_discover_modules_matching.assert_called_with('/path/to/test/sources', '*_tests.py')

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_load_tests_from_discovered_modules(self, mock_discover_modules_matching, mock_unittest):

        mock_modules = Mock()
        mock_discover_modules_matching.return_value = mock_modules

        execute_tests_matching('/path/to/test/sources', '*_tests.py')

        mock_unittest.defaultTestLoader.loadTestsFromNames.assert_called_with(mock_modules)

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_run_discovered_and_loaded_tests(self, mock_discover_modules, mock_unittest):

        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        mock_test_runner = Mock()
        mock_unittest.TextTestRunner.return_value = mock_test_runner

        execute_tests('/path/to/test/sources', '_tests.py')

        mock_test_runner.run.assert_called_with(mock_tests)

    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
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
    @patch('pybuilder.utils.discover_modules')
    def test_should_set_test_method_prefix_when_given(self, mock_discover_modules, mock_unittest):

        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        mock_test_runner = Mock()
        mock_result = Mock()
        mock_test_runner.run.return_value = mock_result
        mock_unittest.TextTestRunner.return_value = mock_test_runner

        actual, _ = execute_tests('/path/to/test/sources', '_tests.py', test_method_prefix='should_')

        self.assertEqual('should_', mock_unittest.defaultTestLoader.testMethodPrefix)
