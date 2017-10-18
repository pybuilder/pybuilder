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
from logging import Logger
from tempfile import NamedTemporaryFile
from unittest import TestCase

from pybuilder.core import Project
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.pylint_plugin import (check_pylint_availability,
                                                    init_pylint,
                                                    execute_pylint,
                                                    DEFAULT_PYLINT_OPTIONS)
from test_utils import Mock, patch


@patch('pybuilder.plugins.python.pylint_plugin.execute_tool_on_modules')
class PylintPluginTests(TestCase):

    def setUp(self):
        self.project = Project(".")
        init_pylint(self.project)
        self.mock_logger = Mock(Logger)

    @patch('pybuilder.plugins.python.pylint_plugin.assert_can_execute')
    def test_should_check_that_pylint_can_be_executed(self, mock_assert_can_execute, mock_execute_tool):
        check_pylint_availability(self.mock_logger)
        expected_command_line = ('pylint',)
        mock_assert_can_execute.assert_called_with(expected_command_line, 'pylint', 'plugin python.pylint')

    def test_should_run_pylint_with_default_options(self, mock_execute_tool):
        self._create_pylint_log_file('E:476, 8: Error message')
        self._run_execute_tool(mock_execute_tool)
        mock_execute_tool.assert_called_with(self.project, "pylint", ["pylint"] + DEFAULT_PYLINT_OPTIONS, True)

    def test_should_run_pylint_with_custom_options(self, mock_execute_tool):
        self._create_pylint_log_file('E:476, 8: Error message')
        self.project.set_property("pylint_options", ["--test", "-f", "--x=y"])
        self._run_execute_tool(mock_execute_tool)
        mock_execute_tool.assert_called_with(self.project, "pylint", ["pylint", "--test", "-f", "--x=y"], True)

    def test_should_show_error_message_in_pyb_logs(self, mock_execute_tool):
        self._create_pylint_log_file('E:476, 8: Error message')
        self._run_execute_tool(mock_execute_tool)
        self.mock_logger.error.assert_called_with('Pylint: Module : E:476, 8: Error message')

    def test_should_show_warning_message_in_pyb_logs(self, mock_execute_tool):
        self._create_pylint_log_file('W:2476, 8: Warning message')
        self.project.set_property('pylint_show_warning_messages', True)
        self._run_execute_tool(mock_execute_tool)
        self.mock_logger.warn.assert_called_with('Pylint: Module : W:2476, 8: Warning message')

    def test_should_break_build_on_errors(self, mock_execute_tool):
        self._create_pylint_log_file('E:2476, 8: Warning message')
        self.project.set_property('pylint_break_build_on_errors', True)
        expected_message = 'Pylint: Building failed due to 1 errors or fatal errors'
        with self.assertRaisesRegexp(BuildFailedException, expected_message):
            self._run_execute_tool(mock_execute_tool)

    def test_should_break_build_on_too_low_pylint_score(self, mock_execute_tool):
        self._create_pylint_log_file('Your code has been rated at 4.60/10 (previous run: 4.60/10, +0.00)')
        self.project.set_property('pylint_score_threshold', 5.0)
        expected_message = 'Pylint: Building failed due to Pylint score\(4.6\) less then expected\(5.0\)'
        with self.assertRaisesRegexp(BuildFailedException, expected_message):
            self._run_execute_tool(mock_execute_tool)

    def test_should_break_build_on_too_high_pylint_score_decrease(self, mock_execute_tool):
        self._create_pylint_log_file('Your code has been rated at 4.60/10 (previous run: 6.60/10, -2.00)')
        self.project.set_property('pylint_score_change_threshold', -1.0)
        expected_message = 'Pylint: Building failed due to Pylint score decrease\(-2.0\) higher then allowed\(-1.0\)'
        with self.assertRaisesRegexp(BuildFailedException, expected_message):
            self._run_execute_tool(mock_execute_tool)

    def _create_pylint_log_file(self, test_file_content):
        self.temp_file = NamedTemporaryFile()
        with open(self.temp_file.name, 'w') as f:
            f.write(test_file_content)

    def _run_execute_tool(self, mock_execute_tool):
        mock_execute_tool.return_value = (0, self.temp_file.name)
        execute_pylint(self.project, self.mock_logger)
