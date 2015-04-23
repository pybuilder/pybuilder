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
from pybuilder.plugins.python.sphinx_plugin import (
    assert_sphinx_is_available,
    assert_sphinx_quickstart_is_available,
    get_sphinx_build_command,
    get_sphinx_quickstart_command,
    initialize_sphinx_plugin
    )


class CheckSphinxAvailableTests(TestCase):

    @patch('pybuilder.plugins.python.sphinx_plugin.assert_can_execute')
    def test_should_check_that_sphinx_can_be_executed(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        assert_sphinx_is_available(mock_logger)

        expected_command_line = ['sphinx-build', '--version']
        mock_assert_can_execute.assert_called_with(
            expected_command_line, 'sphinx', 'plugin python.sphinx')

    @patch('pybuilder.plugins.python.sphinx_plugin.assert_can_execute')
    def test_should_check_that_sphinx_quickstart_can_be_executed(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        assert_sphinx_quickstart_is_available(mock_logger)
        expected_command_line = ['sphinx-quickstart', '--version']
        mock_assert_can_execute.assert_called_with(
            expected_command_line, 'sphinx', 'plugin python.sphinx')


class SphinxPluginInitializationTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "sphinx_source_dir": "source_dir",
            "sphinx_output_dir": "output_dir",
            "sphinx_config_path": "config_path",
            "sphinx_doc_author": "author",
            "sphinx_doc_builder": "doc_builder",
            "sphinx_project_name": "project_name",
            "sphinx_project_version": "project_version"
        }

        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            initialize_sphinx_plugin(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(

                self.project.get_property(property_name),
                property_value)

    def test_should_set_default_values_when_initializing_plugin(self):

        initialize_sphinx_plugin(self.project)

        self.project.set_property("sphinx_project_name", "foo")
        self.project.set_property("sphinx_project_version", "1.0")

        self.assertEquals(self.project.get_property("sphinx_source_dir"), "docs")
        self.assertEquals(self.project.get_property("sphinx_output_dir"), "docs/_build/")
        self.assertEquals(self.project.get_property("sphinx_config_path"), "docs")
        self.assertEquals(self.project.get_property("sphinx_doc_author"), "doc_author")
        self.assertEquals(self.project.get_property("sphinx_doc_builder"), "html")
        self.assertEquals(self.project.get_property("sphinx_project_name"), "foo")
        self.assertEquals(self.project.get_property("sphinx_project_version"), "1.0")


class SphinxBuildCommandTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_generate_sphinx_build_command_per_project_properties(self):

        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", 'JSONx')

        sphinx_build_command = get_sphinx_build_command(self.project)

        self.assertEqual(sphinx_build_command,
                         "sphinx-build -b JSONx basedir/docs/ basedir/docs/_build/")

    def test_should_generate_sphinx_quickstart_command_with_project_properties(self):

        self.project.set_property("sphinx_doc_author", "bar")
        self.project.set_property("sphinx_project_name", "foo")
        self.project.set_property("sphinx_project_version", "3")
        self.project.set_property("sphinx_source_dir", "docs/")

        sphinx_quickstart_command = get_sphinx_quickstart_command(self.project)

        self.assertEqual(sphinx_quickstart_command,
                         "sphinx-quickstart -q -p foo -a bar -v 3 basedir/docs/")
