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

from pybuilder.plugins.python.pyfix_plugin_impl import TestListener


class TestListenerTests(TestCase):

    @patch('pybuilder.plugins.python.pyfix_plugin_impl.execute_tests_matching')
    def test_should_inform_how_many_tests_are_going_to_be_executed(self, mock_execute_tests_matching):

        test_definitions = [Mock(), Mock(), Mock()]
        mock_logger = Mock(Logger)
        listener = TestListener(mock_logger)

        listener.before_suite(test_definitions)

        mock_logger.info.assert_called_with('Running %d pyfix tests', 3)
