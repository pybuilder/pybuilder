from unittest import TestCase
from mock import Mock, patch
from logging import Logger
from pybuilder.core import Project
from pybuilder.plugins.python.snakefood_plugin import (
    depend_on_snakefood,
    check_snakefood_available,
    generate_graph,
    generate_pdf
    )


class CheckSnakeFoodAvailableTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_set_dependency(self):
        mock_project = Mock(Project)
        depend_on_snakefood(mock_project)
        mock_project.build_depends_on.assert_called_with('snakefood')

    @patch('pybuilder.plugins.python.snakefood_plugin.assert_can_execute')
    def test_should_check_that_snakefood_is_available(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        check_snakefood_available(mock_logger)

        mock_assert_can_execute.assert_called_with(
            ('dot', '-V'), 'graphviz', 'plugin python.snakefood')

    @patch('pybuilder.plugins.python.snakefood_plugin.execute_command')
    def test_should_call_generate_graph(self, mock_assert_can_execute):
        report_file = "foo"
        graph_file = "bar.dot"
        generate_graph(report_file, graph_file)

    @patch('pybuilder.plugins.python.snakefood_plugin.execute_command')
    def test_should_call_generate_pdf(self, mock_assert_can_execute):
        pdf_file = "foo.pdf"
        graph_file = "bar.dot"
        generate_pdf(graph_file, pdf_file)
