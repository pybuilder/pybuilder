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

from unittest import TestCase
from logging import Logger
from test_utils import Mock, patch

from pybuilder.core import Project
from pybuilder.plugins.exec_plugin import run_unit_tests, run_integration_tests, analyze, package, publish


@patch('pybuilder.plugins.exec_plugin.run_command')
class SimpleTaskTestS(TestCase):

    def test_should_run_unit_tests(self, mock_run_command):

        mock_project = Mock(Project)
        mock_logger = Mock(Logger)

        run_unit_tests(mock_project, mock_logger)

        mock_run_command.assert_called_with('run_unit_tests', mock_project, mock_logger)

    def test_should_run_integration_tests(self, mock_run_command):

        mock_project = Mock(Project)
        mock_logger = Mock(Logger)

        run_integration_tests(mock_project, mock_logger)

        mock_run_command.assert_called_with('run_integration_tests', mock_project, mock_logger)

    def test_should_analyze_project(self, mock_run_command):

        mock_project = Mock(Project)
        mock_logger = Mock(Logger)

        analyze(mock_project, mock_logger)

        mock_run_command.assert_called_with('analyze', mock_project, mock_logger)

    def test_should_package_project(self, mock_run_command):

        mock_project = Mock(Project)
        mock_logger = Mock(Logger)

        package(mock_project, mock_logger)

        mock_run_command.assert_called_with('package', mock_project, mock_logger)

    def test_should_publish_project(self, mock_run_command):

        mock_project = Mock(Project)
        mock_logger = Mock(Logger)

        publish(mock_project, mock_logger)

        mock_run_command.assert_called_with('publish', mock_project, mock_logger)
