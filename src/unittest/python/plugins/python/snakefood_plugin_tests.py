from unittest import TestCase
from test_utils import Mock, patch, ANY
from logging import Logger
from pybuilder.core import Project
from pybuilder.plugins.python.snakefood_plugin import (
    depend_on_snakefood,
    check_snakefood_available,
    check_graphviz_available,
    generate_graph,
    generate_pdf
    )


class CheckSnakeFoodAvailableTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_set_dependency(self):
        mock_project = Mock(Project)
        depend_on_snakefood(mock_project)
        mock_project.plugin_depends_on.assert_called_with('snakefood')

    @patch('pybuilder.plugins.python.snakefood_plugin.assert_can_execute')
    def test_should_check_that_snakefood_is_available(self, mock_execute_command):

        mock_logger = Mock(Logger)

        check_snakefood_available(self.project, mock_logger)

        mock_execute_command.assert_called_with(
            ("sfood", "-h"), "sfood", "plugin python.snakefood", env=ANY)

    @patch('pybuilder.plugins.python.snakefood_plugin.assert_can_execute')
    def test_should_check_that_graphviz_is_available(self, mock_execute_command):

        mock_logger = Mock(Logger)

        check_graphviz_available(self.project, mock_logger)

        mock_execute_command.assert_called_with(
            ('dot', '-V'), 'graphviz', 'plugin python.snakefood', env=ANY)

    @patch('pybuilder.plugins.python.snakefood_plugin.execute_command')
    def test_should_call_generate_graph(self, mock_execute_command):
        report_file = "foo"
        graph_file = "bar.dot"
        generate_graph(report_file, graph_file)
        mock_execute_command.assert_called_with(
            ["sfood-graph", report_file], graph_file)

    @patch('pybuilder.plugins.python.snakefood_plugin.execute_command')
    def test_should_call_generate_pdf(self, mock_execute_command):
        pdf_file = "foo.pdf"
        graph_file = "bar.dot"
        generate_pdf(graph_file, pdf_file)
        mock_execute_command.assert_called_with(
            ["dot", "-Tpdf", graph_file], pdf_file)
