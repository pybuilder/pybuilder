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
from pybuilder.core import Project
from test_utils import Mock
from pybuilder.plugins.python.flake8_plugin import initialize_flake8_plugin


class FlakePluginInitializationTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_set_dependency(self):
        mock_project = Mock(Project)
        initialize_flake8_plugin(mock_project)
        mock_project.plugin_depends_on.assert_called_with("flake8", "~=3.7")

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "flake8_break_build": True,
            "flake8_max_line_length": 80,
            "flake8_include_patterns": "*.py",
            "flake8_exclude_patterns": ".svn",
            "flake8_include_test_sources": True,
            "flake8_include_scripts": True,
            "flake8_max_complexity": 10
            }
        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            initialize_flake8_plugin(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEqual(
                self.project.get_property("flake8_break_build"), True)
            self.assertEqual(
                self.project.get_property("flake8_max_line_length"), 80)
            self.assertEqual(
                self.project.get_property("flake8_include_patterns"), "*.py")
            self.assertEqual(
                self.project.get_property("flake8_exclude_patterns"), ".svn")
            self.assertEqual(
                self.project.get_property("flake8_include_test_sources"), True)
            self.assertEqual(
                self.project.get_property("flake8_include_scripts"), True)
            self.assertEqual(
                self.project.get_property("flake8_max_complexity"), 10)
