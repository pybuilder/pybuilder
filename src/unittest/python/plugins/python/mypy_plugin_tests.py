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

from unittest import TestCase
from unittest.mock import call

from pybuilder.core import Project, Logger
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.mypy_plugin import (assert_mypy_is_executable,
                                                  initialize_mypy_plugin,
                                                  execute_mypy,
                                                  DEFAULT_MYPY_OPTIONS)
from test_utils import Mock, patch

MYPY_ERROR_OUTPUT = [
    'src/main/python/module/file.py:34: error: "X" is not defined  [name-defined]',
    'src/main/python/module/file.py:42: error: Incompatible return value type (got "int", expected "str")  [return-value]',
    'Found 2 errors in 1 file (checked 10 source files)',
    ''
]

MYPY_NORMAL_OUTPUT = [
    'Success: no issues found in 10 source files',
    ''
]

MYPY_FATAL_ERROR_OUTPUT = [
    'mypy: error: Invalid command line option: --invalid-option',
    ''
]


class MypyPluginTests(TestCase):
    def setUp(self):
        self.project = Project("basedir")
        self.project.set_property("dir_source_main_python", "source")
        self.project.set_property("dir_reports", "reports")

        self.reactor = Mock()
        self.reactor.python_env_registry = {}
        self.reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        pyb_env.environ = {}
        self.reactor.pybuilder_venv = pyb_env

    def test_should_check_that_mypy_can_be_executed(self):
        mock_logger = Mock(Logger)

        assert_mypy_is_executable(self.project, mock_logger, self.reactor)

        self.reactor.pybuilder_venv.verify_can_execute.assert_called_with(
            ['mypy', '--version'], 'mypy', 'plugin python.mypy')

    @patch('pybuilder.plugins.python.mypy_plugin.ExternalCommandBuilder')
    def test_should_run_mypy_with_default_options(self, ecb):
        initialize_mypy_plugin(self.project)

        result = Mock()
        result.exit_code = 0
        result.report_lines = MYPY_NORMAL_OUTPUT
        ecb().run_on_production_source_files.return_value = result

        execute_mypy(self.project, Mock(Logger), self.reactor)

        self.assertEqual(ecb().use_argument.call_args_list,
                         [call(arg) for arg in DEFAULT_MYPY_OPTIONS])

    @patch('pybuilder.plugins.python.mypy_plugin.ExternalCommandBuilder')
    def test_should_run_mypy_with_custom_options(self, ecb):
        initialize_mypy_plugin(self.project)

        result = Mock()
        result.exit_code = 0
        result.report_lines = MYPY_NORMAL_OUTPUT
        ecb().run_on_production_source_files.return_value = result

        self.project.set_property("mypy_options", ["--strict", "--warn-unused-ignores"])

        execute_mypy(self.project, Mock(Logger), self.reactor)

        self.assertEqual(ecb().use_argument.call_args_list,
                         [call(arg) for arg in ["--strict", "--warn-unused-ignores"]])

    @patch('pybuilder.plugins.python.mypy_plugin.ExternalCommandBuilder')
    def test_should_break_build_when_type_errors_and_set(self, ecb):
        initialize_mypy_plugin(self.project)

        result = Mock()
        result.exit_code = 1
        result.report_lines = MYPY_ERROR_OUTPUT
        ecb().run_on_production_source_files.return_value = result

        self.project.set_property("mypy_break_build", True)

        with self.assertRaises(BuildFailedException):
            execute_mypy(self.project, Mock(Logger), self.reactor)

    @patch('pybuilder.plugins.python.mypy_plugin.ExternalCommandBuilder')
    def test_should_not_break_build_when_type_errors_and_not_set(self, ecb):
        initialize_mypy_plugin(self.project)

        result = Mock()
        result.exit_code = 1
        result.report_lines = MYPY_ERROR_OUTPUT
        ecb().run_on_production_source_files.return_value = result

        self.project.set_property("mypy_break_build", False)

        execute_mypy(self.project, Mock(Logger), self.reactor)

    @patch('pybuilder.plugins.python.mypy_plugin.ExternalCommandBuilder')
    def test_should_not_break_build_when_no_errors(self, ecb):
        initialize_mypy_plugin(self.project)

        result = Mock()
        result.exit_code = 0
        result.report_lines = MYPY_NORMAL_OUTPUT
        ecb().run_on_production_source_files.return_value = result

        self.project.set_property("mypy_break_build", True)

        execute_mypy(self.project, Mock(Logger), self.reactor)

    @patch('pybuilder.plugins.python.mypy_plugin.ExternalCommandBuilder')
    def test_should_always_break_build_on_fatal_mypy_error(self, ecb):
        initialize_mypy_plugin(self.project)

        result = Mock()
        result.exit_code = 2
        result.report_lines = MYPY_FATAL_ERROR_OUTPUT
        ecb().run_on_production_source_files.return_value = result

        self.project.set_property("mypy_break_build", True)

        with self.assertRaises(BuildFailedException):
            execute_mypy(self.project, Mock(Logger), self.reactor)

    @patch('pybuilder.plugins.python.mypy_plugin.ExternalCommandBuilder')
    def test_should_always_fail_build_on_fatal_error_regardless_of_break_build(self, ecb):
        initialize_mypy_plugin(self.project)

        result = Mock()
        result.exit_code = 2
        result.report_lines = MYPY_FATAL_ERROR_OUTPUT
        ecb().run_on_production_source_files.return_value = result

        self.project.set_property("mypy_break_build", False)

        with self.assertRaises(BuildFailedException):
            execute_mypy(self.project, Mock(Logger), self.reactor)
