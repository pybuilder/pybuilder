#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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

from fluentmock import UnitTests, when, verify, NEVER
from mock import Mock

from pybuilder.core import Project
from pybuilder.plugins.filter_resources_plugin import ProjectDictWrapper


class ProjectDictWrapperTest(UnitTests):

    def test_should_return_project_property_when_property_is_defined(self):
        project_mock = Mock(Project)
        project_mock.name = "my name"

        self.assertEquals("my name", ProjectDictWrapper(project_mock, Mock())["name"])

        verify(project_mock, NEVER).get_property("name", "name")

    def test_should_delegate_to_project_get_property_when_attribute_is_not_defined(self):
        project_mock = Project(".")
        when(project_mock).has_property("spam").then_return(True)
        when(project_mock).get_property("spam").then_return("eggs")

        self.assertEquals("eggs", ProjectDictWrapper(project_mock, Mock())["spam"])

        verify(project_mock).get_property("spam")

    def test_should_warn_when_substitution_is_skipped(self):
        project_mock = Project(".")
        logger_mock = Mock()
        when(project_mock).has_property("n/a").then_return(False)

        self.assertEquals("${n/a}", ProjectDictWrapper(project_mock, logger_mock)["n/a"])

        verify(project_mock, NEVER).get_property("n/a")
        verify(logger_mock).warn(
            "Skipping impossible substitution for 'n/a' - there is no matching project attribute or property.")
