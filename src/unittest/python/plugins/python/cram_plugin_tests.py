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

import unittest
from os.path import normcase as nc, pathsep

from pybuilder.core import Project
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.cram_plugin import (
    _cram_command_for,
    _find_files,
    _report_file,
    run_cram_tests,
)
from test_utils import patch, Mock, call


class CramPluginTests(unittest.TestCase):
    def test_command_respects_no_verbose(self):
        project = Project('.')
        project.set_property('verbose', False)
        expected = ['-m', 'cram', '-E']
        received = _cram_command_for(project)
        self.assertEqual(expected, received)

    def test_command_respects_verbose(self):
        project = Project('.')
        project.set_property('verbose', True)
        expected = ['-m', 'cram', '-E', '--verbose']
        received = _cram_command_for(project)
        self.assertEqual(expected, received)

    @patch('pybuilder.plugins.python.cram_plugin.discover_files_matching')
    def test_find_files(self, discover_mock):
        project = Project('.')
        project.set_property('dir_source_cmdlinetest', nc('/any/dir'))
        project.set_property('cram_test_file_glob', '*.t')
        expected = [nc('./any/dir/test.cram')]
        discover_mock.return_value = expected
        received = _find_files(project)
        self.assertEqual(expected, received)
        discover_mock.assert_called_once_with(nc('/any/dir'), '*.t')

    def test_report(self):
        project = Project('.')
        project.set_property('dir_reports', '/any/dir')
        expected = nc('./any/dir/cram.err')
        received = _report_file(project)
        self.assertEqual(expected, received)

    @patch('pybuilder.plugins.python.cram_plugin._cram_command_for')
    @patch('pybuilder.plugins.python.cram_plugin._find_files')
    @patch('pybuilder.plugins.python.cram_plugin._report_file')
    @patch('pybuilder.plugins.python.cram_plugin.read_file')
    def test_running_plugin_cram_from_target(self,
                                             read_file_mock,
                                             report_mock,
                                             find_files_mock,
                                             command_mock
                                             ):
        project = Project('.')
        project.set_property('cram_run_test_from_target', True)
        project.set_property('dir_dist', 'python')
        project.set_property('dir_dist_scripts', 'scripts')
        project.set_property('verbose', False)
        project._plugin_env = {}
        logger = Mock()

        reactor = Mock()
        reactor.python_env_registry = {}
        reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        reactor.pybuilder_venv = pyb_env
        pyb_env.environ = {}
        pyb_env.executable = ["a/b"]
        execute_mock = pyb_env.execute_command = Mock()

        command_mock.return_value = ['cram']
        find_files_mock.return_value = ['test1.cram', 'test2.cram']
        report_mock.return_value = 'report_file'
        read_file_mock.return_value = ['test failes for file', '# results']
        execute_mock.return_value = 0

        run_cram_tests(project, logger, reactor)
        execute_mock.assert_called_once_with(
            ['a/b', 'cram', 'test1.cram', 'test2.cram'], 'report_file',
            error_file_name='report_file',
            env={'PYTHONPATH': nc('./python' + pathsep), 'PATH': nc('./python/scripts' + pathsep)}
        )
        expected_info_calls = [call('Running Cram command line tests'),
                               call('Cram tests were fine'),
                               call('results'),
                               ]
        self.assertEqual(expected_info_calls, logger.info.call_args_list)

    @patch('pybuilder.plugins.python.cram_plugin._cram_command_for')
    @patch('pybuilder.plugins.python.cram_plugin._find_files')
    @patch('pybuilder.plugins.python.cram_plugin._report_file')
    @patch('pybuilder.plugins.python.cram_plugin.read_file')
    def test_running_plugin_from_scripts(self,
                                         read_file_mock,
                                         report_mock,
                                         find_files_mock,
                                         command_mock
                                         ):
        project = Project('.')
        project.set_property('cram_run_test_from_target', False)
        project.set_property('dir_source_main_python', 'python')
        project.set_property('dir_source_main_scripts', 'scripts')
        project.set_property('verbose', False)
        project._plugin_env = {}
        logger = Mock()
        reactor = Mock()
        reactor.python_env_registry = {}
        reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        reactor.pybuilder_venv = pyb_env
        pyb_env.environ = {}
        pyb_env.executable = ["a/b"]
        execute_mock = pyb_env.execute_command = Mock()

        command_mock.return_value = ['cram']
        find_files_mock.return_value = ['test1.cram', 'test2.cram']
        report_mock.return_value = 'report_file'
        read_file_mock.return_value = ['test fails for file', '# results']
        execute_mock.return_value = 0

        run_cram_tests(project, logger, reactor)
        execute_mock.assert_called_once_with(
            ['a/b', 'cram', 'test1.cram', 'test2.cram'], 'report_file',
            error_file_name='report_file',
            env={'PYTHONPATH': nc('./python' + pathsep), 'PATH': nc('./scripts' + pathsep)}
        )
        expected_info_calls = [call('Running Cram command line tests'),
                               call('Cram tests were fine'),
                               call('results'),
                               ]
        self.assertEqual(expected_info_calls, logger.info.call_args_list)

    @patch('pybuilder.plugins.python.cram_plugin.tail_log')
    @patch('pybuilder.plugins.python.cram_plugin._cram_command_for')
    @patch('pybuilder.plugins.python.cram_plugin._find_files')
    @patch('pybuilder.plugins.python.cram_plugin._report_file')
    @patch('pybuilder.plugins.python.cram_plugin.read_file')
    def test_running_plugin_fails(self,
                                  read_file_mock,
                                  report_mock,
                                  find_files_mock,
                                  command_mock,
                                  tail_mock,
                                  ):
        project = Project('.')
        project.set_property('verbose', False)
        project.set_property('dir_source_main_python', 'python')
        project.set_property('dir_source_main_scripts', 'scripts')

        logger = Mock()
        reactor = Mock()
        reactor.python_env_registry = {}
        reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        reactor.pybuilder_venv = pyb_env
        pyb_env.environ = {}
        pyb_env.executable = ["a/b"]
        execute_mock = pyb_env.execute_command = Mock()

        command_mock.return_value = ['cram']
        find_files_mock.return_value = ['test1.cram', 'test2.cram']
        report_mock.return_value = 'report_file'
        read_file_mock.return_value = ['test failes for file', '# results']
        execute_mock.return_value = 1
        tail_mock.return_value = "tail data"

        self.assertRaises(
            BuildFailedException, run_cram_tests, project, logger, reactor)
        execute_mock.assert_called_once_with(
            ['a/b', 'cram', 'test1.cram', 'test2.cram'], 'report_file',
            error_file_name='report_file',
            env={'PYTHONPATH': nc('./python' + pathsep), 'PATH': nc('./scripts' + pathsep)}
        )
        expected_info_calls = [call('Running Cram command line tests'),
                               ]
        expected_error_calls = [call('Cram tests failed! See report_file for full details:\ntail data'),
                                ]
        self.assertEqual(expected_info_calls, logger.info.call_args_list)
        self.assertEqual(expected_error_calls, logger.error.call_args_list)

    @patch('pybuilder.plugins.python.cram_plugin._cram_command_for')
    @patch('pybuilder.plugins.python.cram_plugin._find_files')
    @patch('pybuilder.plugins.python.cram_plugin._report_file')
    @patch('pybuilder.plugins.python.cram_plugin.read_file')
    def test_running_plugin_no_failure_no_tests(self,
                                                read_file_mock,
                                                report_mock,
                                                find_files_mock,
                                                command_mock
                                                ):
        project = Project('.')
        project.set_property('verbose', True)
        project.set_property('dir_source_main_python', 'python')
        project.set_property('dir_source_main_scripts', 'scripts')
        project.set_property("cram_fail_if_no_tests", False)
        project._plugin_env = {}
        logger = Mock()
        reactor = Mock()
        reactor.python_env_registry = {}
        reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        reactor.pybuilder_venv = pyb_env
        pyb_env.environ = {}
        pyb_env.executable = ["a/b"]
        execute_mock = pyb_env.execute_command = Mock()

        command_mock.return_value = ['cram']
        find_files_mock.return_value = []
        report_mock.return_value = 'report_file'
        read_file_mock.return_value = ['test failes for file', '# results']
        execute_mock.return_value = 1

        run_cram_tests(project, logger, reactor)

        execute_mock.assert_not_called()
        expected_info_calls = [call('Running Cram command line tests'),
                               ]
        self.assertEqual(expected_info_calls, logger.info.call_args_list)

    @patch('pybuilder.plugins.python.cram_plugin._cram_command_for')
    @patch('pybuilder.plugins.python.cram_plugin._find_files')
    @patch('pybuilder.plugins.python.cram_plugin._report_file')
    @patch('pybuilder.plugins.python.cram_plugin.read_file')
    def test_running_plugin_failure_no_tests(self,
                                             read_file_mock,
                                             report_mock,
                                             find_files_mock,
                                             command_mock
                                             ):
        project = Project('.')
        project.set_property('verbose', True)
        project.set_property('dir_source_main_python', 'python')
        project.set_property('dir_source_main_scripts', 'scripts')
        project.set_property("cram_fail_if_no_tests", True)
        project._plugin_env = {}
        logger = Mock()
        reactor = Mock()
        reactor.python_env_registry = {}
        reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        pyb_env.environ = {}
        execute_mock = pyb_env.execute_command = Mock()

        command_mock.return_value = ['cram']
        find_files_mock.return_value = []
        report_mock.return_value = 'report_file'
        read_file_mock.return_value = ['test failes for file', '# results']
        execute_mock.return_value = 1

        self.assertRaises(
            BuildFailedException, run_cram_tests, project, logger, reactor)

        execute_mock.assert_not_called()
        expected_info_calls = [call('Running Cram command line tests'),
                               ]
        self.assertEqual(expected_info_calls, logger.info.call_args_list)
