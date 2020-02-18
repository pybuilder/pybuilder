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

from logging import Logger
from unittest import TestCase

from pybuilder.core import Project
from pybuilder.plugins.python.snakefood_plugin import (
    check_snakefood_available,
    check_graphviz_available,
    generate_graph,
    generate_pdf
)
from test_utils import Mock


class CheckSnakeFoodAvailableTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

        self.reactor = Mock()
        self.reactor.python_env_registry = {}
        self.reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        pyb_env.environ = {}
        self.reactor.pybuilder_venv = pyb_env

    def test_should_check_that_snakefood_is_available(self):
        mock_logger = Mock(Logger)

        check_snakefood_available(self.project, mock_logger, self.reactor)

        self.reactor.pybuilder_venv.verify_can_execute.assert_called_with(
            ["sfood", "-h"], "sfood", "plugin python.snakefood")

    def test_should_check_that_graphviz_is_available(self):
        mock_logger = Mock(Logger)

        check_graphviz_available(self.project, mock_logger, self.reactor)

        self.reactor.pybuilder_venv.verify_can_execute.assert_called_with(
            ["dot", "-V"], "graphviz", "plugin python.snakefood")

    def test_should_call_generate_graph(self):
        report_file = "foo"
        graph_file = "bar.dot"

        generate_graph(self.reactor.pybuilder_venv, report_file, graph_file)

        self.reactor.pybuilder_venv.execute_command.assert_called_with(
            ["sfood-graph", report_file], graph_file)

    def test_should_call_generate_pdf(self):
        pdf_file = "foo.pdf"
        graph_file = "bar.dot"

        generate_pdf(self.reactor.pybuilder_venv, graph_file, pdf_file)

        self.reactor.pybuilder_venv.execute_command.assert_called_with(
            ["dot", "-Tpdf", graph_file], pdf_file)
