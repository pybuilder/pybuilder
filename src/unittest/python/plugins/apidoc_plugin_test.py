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
from pybuilder.core import Project
from test_utils import Mock, patch
from logging import Logger
from pybuilder.plugins.apidoc_plugin import (
    build_apidoc_command,
    assert_apidoc_is_executable,
    init_apidoc_plugin,
)


class ApidocPluginTests(TestCase):
    """Should test plugin configuration."""

    def test_should_generate_command_abiding_to_configuration(self):
        """Verify configuration defaults."""
        project = Project('egg')
        project.set_property_if_unset('apidoc_output_folder', 'docs/')
        project.set_property_if_unset(
            'apidoc_src_folder',
            'src/main/python/')

        self.assertEqual(
            build_apidoc_command(project),
            'apidoc -i src/main/python/ -o docs/')


class ApidocInitializationTests(TestCase):
    """Should test plugin functionality."""

    def setUp(self):
        """Unitesting Setup."""
        self.project = Project("basedir")

    def test_should_leave_user_specified_properties_when_initializing(self):
        """Should check that the user is able to change default properties."""
        expected_properties = {
            "apidoc_output_folder": "foo",
            "apidoc_src_folder": "bar",
        }

        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            init_apidoc_plugin(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(

                self.project.get_property(property_name),
                property_value)

    @patch('pybuilder.plugins.apidoc_plugin.assert_can_execute')
    def test_should_check_that_apidoc_is_executable(self,
                                                    mock_assert_can_execute):
        """Check that apidoc module is installed."""
        mock_logger = Mock(Logger)

        assert_apidoc_is_executable(mock_logger)

        mock_assert_can_execute.assert_called_with(
            caller='plugin apidoc_plugin',
            command_and_arguments=['apidoc', '--h'],
            prerequisite='apidoc')
