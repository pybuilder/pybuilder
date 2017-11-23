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

import unittest

from pybuilder.core import Project
from pybuilder.plugins.filter_resources_plugin import ProjectDictWrapper
from test_utils import Mock


class ProjectDictWrapperTest(unittest.TestCase):
    def test_should_return_project_property_when_property_is_defined(self):
        project_mock = Mock(Project)
        project_mock.name = "my name"

        self.assertEqual("my name", ProjectDictWrapper(project_mock, Mock())["name"])

        project_mock.get_property.assert_not_called()

    def test_should_delegate_to_project_get_property_when_attribute_is_not_defined(self):
        project_mock = Project(".")
        project_mock.has_property = Mock(return_value=True)
        project_mock.get_property = Mock(return_value="eggs")

        self.assertEqual("eggs", ProjectDictWrapper(project_mock, Mock())["spam"])

        project_mock.get_property.assert_called_with("spam")

    def test_should_warn_when_substitution_is_skipped(self):
        project_mock = Project(".")
        logger_mock = Mock()
        project_mock.has_property = Mock(return_value=False)
        project_mock.get_property = Mock()

        self.assertEqual("${n/a}", ProjectDictWrapper(project_mock, logger_mock)["n/a"])

        project_mock.get_property.assert_not_called()
        logger_mock.warn.assert_called_with(
            "Skipping impossible substitution for 'n/a' - there is no matching project attribute or property.")
