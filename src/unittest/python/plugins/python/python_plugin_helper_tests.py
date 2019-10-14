#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2019 PyBuilder Team
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

import unittest

from pybuilder.plugins.python.python_plugin_helper import (log_report,
                                                           discover_affected_files,
                                                           discover_affected_dirs,
                                                           execute_tool_on_source_files,
                                                           _if_property_set_and_dir_exists)
from test_utils import Mock, call, patch, ANY


class LogReportsTest(unittest.TestCase):
    def test_should_not_warn_when_report_lines_is_empty(self):
        logger = Mock()
        log_report(logger, 'name', [])

        self.assertFalse(logger.warn.called)

    def test_should_warn_when_report_lines_present(self):
        logger = Mock()
        log_report(logger, 'name', ['line1 ', 'line 2 '])

        self.assertEqual(logger.warn.call_args_list,
                         [call('name: line1'), call('name: line 2')])


class DiscoverAffectedFilesTest(unittest.TestCase):
    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_not_included(self, discover_python_files):
        project = Mock()
        project.get_property.return_value = 'source_directory'
        discover_python_files.return_value = ['foo.py', 'bar.py']

        files = discover_affected_files(False, False, project)
        discover_python_files.assert_called_with('source_directory')
        self.assertEqual(files, ['foo.py', 'bar.py'])

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_are_included(self, discover_python_files):
        project = Mock()

        project.get_property.side_effect = lambda _property: _property

        discover_affected_files(True, False, project)

        self.assertEqual(discover_python_files.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_unittest_python'),
                          call('dir_source_integrationtest_python')])

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    @patch('pybuilder.plugins.python.python_plugin_helper.discover_files_matching')
    def test_should_discover_source_files_when_scripts_are_included(self, discover_files_matching, _):
        project = Mock()

        project.get_property.return_value = True
        project.get_property.side_effect = lambda _property: _property

        discover_affected_files(False, True, project)

        discover_files_matching.assert_called_with('dir_source_main_scripts', '*')

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_are_included_and_only_unittests(self,
                                                                                            discover_python_files):
        project = Mock()

        def get_property(property):
            if property == 'dir_source_integrationtest_python':
                return None
            return property

        project.get_property.side_effect = get_property

        discover_affected_files(True, False, project)

        self.assertEqual(discover_python_files.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_unittest_python')])

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_are_included_and_only_integrationtests(self,
                                                                                                   discover_python_files):
        project = Mock()

        def get_property(property):
            if property == 'dir_source_unittest_python':
                return None
            return property

        project.get_property.side_effect = get_property

        discover_affected_files(True, False, project)

        self.assertEqual(discover_python_files.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_integrationtest_python')])

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_are_included_and_no_tests(self, discover_python_files):
        project = Mock()

        def get_property(property):
            if property == 'dir_source_main_python':
                return property
            return None

        project.get_property.side_effect = get_property

        discover_affected_files(True, False, project)

        self.assertEqual(discover_python_files.call_args_list,
                         [call('dir_source_main_python')])


class DiscoverAffectedDirsTest(unittest.TestCase):
    def test_should_discover_source_dirs_when_test_sources_not_included(self):
        project = Mock()
        project.get_property.return_value = 'source_directory'

        files = discover_affected_dirs(False, False, project)
        self.assertEqual(files, ['source_directory'])

    @patch('pybuilder.plugins.python.python_plugin_helper.os.path.isdir', return_value=True)
    def test_should_discover_source_dirs_when_test_sources_are_included(self, _):
        project = Mock()

        project.get_property.side_effect = lambda _property: _property

        files = discover_affected_dirs(True, False, project)

        self.assertEqual(project.get_property.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_unittest_python'),
                          call('dir_source_unittest_python'),
                          call('dir_source_integrationtest_python'),
                          call('dir_source_integrationtest_python')])
        self.assertEqual(files,
                         ['dir_source_main_python', 'dir_source_unittest_python', 'dir_source_integrationtest_python'])

    @patch('pybuilder.plugins.python.python_plugin_helper.os.path.isdir', return_value=True)
    def test_should_discover_source_dirs_when_test_sources_are_included_no_unittests(self, _):
        project = Mock()

        project.get_property.side_effect = lambda _property: (
            _property if _property != 'dir_source_unittest_python' else None)

        files = discover_affected_dirs(True, False, project)

        self.assertEqual(project.get_property.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_unittest_python'),
                          call('dir_source_integrationtest_python'),
                          call('dir_source_integrationtest_python')])
        self.assertEqual(files,
                         ['dir_source_main_python', 'dir_source_integrationtest_python'])

    @patch('pybuilder.plugins.python.python_plugin_helper.os.path.isdir', return_value=True)
    def test_should_discover_source_dirs_when_test_sources_are_included_no_integrationtests(self, _):
        project = Mock()

        project.get_property.side_effect = lambda _property: (
            _property if _property != 'dir_source_integrationtest_python' else None)

        files = discover_affected_dirs(True, False, project)

        self.assertEqual(project.get_property.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_unittest_python'),
                          call('dir_source_unittest_python'),
                          call('dir_source_integrationtest_python')])
        self.assertEqual(files,
                         ['dir_source_main_python', 'dir_source_unittest_python'])

    @patch('pybuilder.plugins.python.python_plugin_helper.os.path.isdir', return_value=True)
    def test_should_discover_source_dirs_when_script_sources_are_included(self, _):
        project = Mock()

        project.get_property.side_effect = lambda _property: (
            _property if _property != 'dir_source_integrationtest_python' else None)

        files = discover_affected_dirs(False, True, project)

        self.assertEqual(project.get_property.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_main_scripts'),
                          call('dir_source_main_scripts')])
        self.assertEqual(files,
                         ['dir_source_main_python', 'dir_source_main_scripts'])

    @patch('pybuilder.plugins.python.python_plugin_helper.os.path.isdir', return_value=True)
    def test_if_property_set_and_dir_exists(self, exists):
        self.assertTrue(_if_property_set_and_dir_exists('test'))
        exists.assert_called_once_with('test')

    @patch('pybuilder.plugins.python.python_plugin_helper.os.path.isdir', return_value=False)
    def test_if_property_set_and_dir_not_exists(self, exists):
        self.assertFalse(_if_property_set_and_dir_exists('test'))
        exists.assert_called_once_with('test')

    @patch('pybuilder.plugins.python.python_plugin_helper.os.path.isdir', return_value=False)
    def test_if_property_not_set_and_dir_not_exists(self, exists):
        self.assertFalse(_if_property_set_and_dir_exists(None))
        exists.assert_not_called()


class ExecuteToolOnSourceFilesTest(unittest.TestCase):
    @patch('pybuilder.plugins.python.python_plugin_helper.log_report')
    @patch('pybuilder.plugins.python.python_plugin_helper.read_file')
    @patch('pybuilder.plugins.python.python_plugin_helper.execute_command')
    @patch('pybuilder.plugins.python.python_plugin_helper.discover_affected_files')
    def test_should_execute_tool_on_source_files(self, affected,
                                                 execute, read, log):
        project = Mock()
        project.expand_path.return_value = '/path/to/report'
        affected.return_value = ['file1', 'file2']

        execute_tool_on_source_files(project, 'name', 'foo --bar')

        execute.assert_called_with(['foo --bar', 'file1', 'file2'], '/path/to/report', env=ANY)

    @patch('pybuilder.plugins.python.python_plugin_helper.log_report')
    @patch('pybuilder.plugins.python.python_plugin_helper.read_file')
    @patch('pybuilder.plugins.python.python_plugin_helper.execute_command')
    @patch('pybuilder.plugins.python.python_plugin_helper.discover_affected_dirs')
    def test_should_execute_tool_on_source_dirs(self, affected,
                                                execute, read, log):
        project = Mock()
        project.expand_path.return_value = '/path/to/report'
        affected.return_value = ['/dir1', '/dir2']

        execute_tool_on_source_files(project, 'name', 'foo --bar', include_dirs_only=True)

        execute.assert_called_with(['foo --bar', '/dir1', '/dir2'], '/path/to/report', env=ANY)

    @patch('pybuilder.plugins.python.python_plugin_helper.log_report')
    @patch('pybuilder.plugins.python.python_plugin_helper.read_file')
    @patch('pybuilder.plugins.python.python_plugin_helper.execute_command')
    @patch('pybuilder.plugins.python.python_plugin_helper.discover_affected_files')
    def test_should_give_verbose_output(self, affected,
                                        execute, read, log):
        project = Mock()
        project.get_property.return_value = True  # flake8_verbose_output == True
        logger = Mock()
        read.return_value = ['error', 'warning']

        execute_tool_on_source_files(project, 'flake8', 'foo --bar', logger)

        log.assert_called_with(logger, 'flake8', ['error', 'warning'])
