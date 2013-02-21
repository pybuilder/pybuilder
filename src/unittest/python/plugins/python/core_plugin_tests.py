#  This file is part of Python Builder
#
#  Copyright 2011-2013 PyBuilder Team
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

from pybuilder.plugins.python.core_plugin import init_python_directories
from pybuilder.plugins.python.core_plugin import DISTRIBUTION_PROPERTY, PYTHON_SOURCES_PROPERTY, SCRIPTS_SOURCES_PROPERTY, SCRIPTS_TARGET_PROPERTY

from pybuilder.core import Project

class InitPythonDirectoriesTest (unittest.TestCase):
    def setUp(self):
        self.project = Project(".")

    def test_should_set_python_sources_property(self):
        init_python_directories(self.project)
        self.assertEquals("src/main/python", self.project.get_property(PYTHON_SOURCES_PROPERTY, "caboom"))

    def test_should_set_scripts_sources_property(self):
        init_python_directories(self.project)
        self.assertEquals("src/main/scripts", self.project.get_property(SCRIPTS_SOURCES_PROPERTY, "caboom"))

    def test_should_set_dist_scripts_property(self):
        init_python_directories(self.project)
        self.assertEquals(None, self.project.get_property(SCRIPTS_TARGET_PROPERTY, "caboom"))

    def test_should_set_dist_property(self):
        init_python_directories(self.project)
        self.assertEquals("$dir_target/dist/.-1.0-SNAPSHOT", self.project.get_property(DISTRIBUTION_PROPERTY, "caboom"))
