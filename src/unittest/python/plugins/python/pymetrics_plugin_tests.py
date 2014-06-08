#   -*- coding: utf-8 -*-
#
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

from unittest import TestCase
from mock import Mock, patch
from logging import Logger

from pybuilder.plugins.python.pymetrics_plugin import check_pymetrics_available


class TestListenerTests(TestCase):

    @patch('pybuilder.plugins.python.pymetrics_plugin.assert_can_execute')
    def test_should_check_that_pymetrics_can_be_executed(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        check_pymetrics_available(mock_logger)

        expected_command_line = ('pymetrics', '--nosql', '--nocsv')
        mock_assert_can_execute.assert_called_with(expected_command_line, 'pymetrics', 'plugin python.pymetrics')
