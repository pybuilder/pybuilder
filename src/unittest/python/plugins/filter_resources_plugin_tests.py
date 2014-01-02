#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from mockito import when, verify, never
from test_utils import mock

from pybuilder.core import Project
from pybuilder.plugins.filter_resources_plugin import ProjectDictWrapper


class ProjectDictWrapperTest (unittest.TestCase):

    def test_should_return_project_property_when_property_is_defined(self):
        project_mock = mock(Project, name="my name")

        self.assertEquals("my name", ProjectDictWrapper(project_mock)["name"])

        verify(project_mock, never).get_property("name", "name")

    def test_should_delegate_to_project_get_property_when_attribute_is_not_defined(self):
        project_mock = Project(".")
        when(project_mock).get_property("spam", "spam").thenReturn("eggs")

        self.assertEquals("eggs", ProjectDictWrapper(project_mock)["spam"])

        verify(project_mock).get_property("spam", "spam")
