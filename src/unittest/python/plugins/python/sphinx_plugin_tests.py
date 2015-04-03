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
from mock import Mock, patch
from logging import Logger

from pybuilder.core import Project
from pybuilder.plugins.python.sphinx_plugin import assert_sphinx_is_available
from pybuilder.plugins.python.sphinx_plugin import assert_sphinx_quickstart_is_available
from pybuilder.plugins.python.sphinx_plugin import get_sphinx_build_command
from pybuilder.plugins.python.sphinx_plugin import get_sphinx_quickstart_command


class CheckSphinxAvailableTests(TestCase):

    @patch('pybuilder.plugins.python.sphinx_plugin.assert_can_execute')
    def test_should_check_that_sphinx_can_be_executed(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        assert_sphinx_is_available(mock_logger)

        expected_command_line = ['sphinx-build', '--version']
        mock_assert_can_execute.assert_called_with(expected_command_line, 'sphinx', 'plugin python.sphinx')


class test_should_check_that_sphinx_quickstart_can_be_executed(TestCase):

    @patch('pybuilder.plugins.python.sphinx_plugin.assert_can_execute')
    def test_should_check_that_sphinx_quickstart_can_be_executed(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        assert_sphinx_quickstart_is_available(mock_logger)
        expected_command_line = ['sphinx-quickstart', '--version']
        mock_assert_can_execute.assert_called_with(expected_command_line, 'sphinx', 'plugin python.sphinx')


class SphinxBuildCommandTests(TestCase):

    def test_should_generate_sphinx_build_command_per_project_properties(self):
        project = Project('basedir')
        setattr(project, 'doc_builder', 'html')

        project.set_property("sphinx_config_path", "docs/")
        project.set_property("sphinx_source_dir", "docs/")
        project.set_property("sphinx_output_dir", "docs/_build/")

        sphinx_build_command = get_sphinx_build_command(project)

        self.assertEqual(sphinx_build_command,
                         "sphinx-build -b html basedir/docs/ basedir/docs/_build/")

    def test_should_generate_sphinx_quickstart_command_with_project_properties(self):
        project = Project('basedir')
        setattr(project, 'doc_author', 'bar')
        setattr(project, 'version', '3')
        setattr(project, 'name', 'foo')

        project.set_property("project.name", "foo")
        project.set_property("project.version", "3")
        project.set_property("sphinx_source_dir", "docs/")

        sphinx_quickstart_command = get_sphinx_quickstart_command(project)

        self.assertEqual(sphinx_quickstart_command,
                         "sphinx-quickstart -q -p foo -a bar -v 3 basedir/docs/")
