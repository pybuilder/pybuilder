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
from mock import Mock, patch
from logging import Logger
from pybuilder.plugins.ronn_manpage_plugin import (
    build_generate_manpages_command,
    init_ronn_manpage_plugin,
    assert_ronn_is_executable,
    assert_gzip_is_executable
    )


class RonnManpagePluginTests(TestCase):

    def test_should_generate_command_abiding_to_configuration(self):
        project = Project('egg')
        project.set_property("dir_manpages", "docs/man")
        project.set_property("manpage_source", "README.md")
        project.set_property("manpage_section", 1)

        self.assertEqual(build_generate_manpages_command(project), 'ronn -r --pipe README.md | gzip -9 > docs/man/egg.1.gz')


class RonnPluginInitializationTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "dir_manpages": "foo",
            "manpage_source": "bar",
            "manpage_section": 1
        }

        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            init_ronn_manpage_plugin(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(

                self.project.get_property(property_name),
                property_value)

    @patch('pybuilder.plugins.ronn_manpage_plugin.assert_can_execute')
    def test_should_check_that_ronn_is_executable(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        assert_ronn_is_executable(mock_logger)
        mock_assert_can_execute.assert_called_with(
            caller='plugin ronn_manpage_plugin',
            command_and_arguments=['ronn', '--version'],
            prerequisite='ronn')

    @patch('pybuilder.plugins.ronn_manpage_plugin.assert_can_execute')
    def test_should_check_that_gzip_is_excecuteble(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        assert_gzip_is_executable(mock_logger)
        mock_assert_can_execute.assert_called_with(
            caller="plugin ronn_manpage_plugin",
            command_and_arguments=["gzip", "--version"],
            prerequisite="gzip")
