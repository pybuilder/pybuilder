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

from unittest import TestCase
from test_utils import Mock, patch
from logging import Logger

from pybuilder.core import Project
from pybuilder.plugins.python.pylint_plugin import (check_pylint_availability,
                                                    init_pylint,
                                                    execute_pylint,
                                                    DEFAULT_PYLINT_OPTIONS)


class PylintPluginTests(TestCase):

    @patch('pybuilder.plugins.python.pylint_plugin.assert_can_execute')
    def test_should_check_that_pylint_can_be_executed(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        check_pylint_availability(mock_logger)

        expected_command_line = ('pylint',)
        mock_assert_can_execute.assert_called_with(expected_command_line, 'pylint', 'plugin python.pylint')

    @patch('pybuilder.plugins.python.pylint_plugin.execute_tool_on_modules')
    def test_should_run_pylint_with_default_options(self, execute_tool):
        project = Project(".")
        init_pylint(project)

        execute_pylint(project, Mock(Logger))

        execute_tool.assert_called_with(project, "pylint", ["pylint"] + DEFAULT_PYLINT_OPTIONS, True)

    @patch('pybuilder.plugins.python.pylint_plugin.execute_tool_on_modules')
    def test_should_run_pylint_with_custom_options(self, execute_tool):
        project = Project(".")
        init_pylint(project)
        project.set_property("pylint_options", ["--test", "-f", "--x=y"])

        execute_pylint(project, Mock(Logger))

        execute_tool.assert_called_with(project, "pylint", ["pylint", "--test", "-f", "--x=y"], True)
