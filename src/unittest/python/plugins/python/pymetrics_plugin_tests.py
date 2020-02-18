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

from pybuilder.core import Project, Logger
from pybuilder.plugins.python.pymetrics_plugin import check_pymetrics_available
from test_utils import Mock


class CheckMyMetricsAvailableTests(TestCase):

    def test_should_check_that_pymetrics_can_be_executed(self):
        mock_project = Mock(Project)
        mock_logger = Mock(Logger)

        reactor = Mock()
        reactor.python_env_registry = {}
        reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        pyb_env.environ = {}
        verify_mock = pyb_env.verify_can_execute = Mock()
        reactor.pybuilder_venv = pyb_env

        check_pymetrics_available(mock_project, mock_logger, reactor)

        verify_mock.assert_called_with(["pymetrics", "--nosql", "--nocsv"], "pymetrics", "plugin python.pymetrics")
