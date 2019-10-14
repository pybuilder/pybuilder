#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2019 PyBuilder Team
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
from os.path import join

from pybuilder.core import Project
from pybuilder.plugins.python.core_plugin import (DISTRIBUTION_PROPERTY,
                                                  PYTHON_SOURCES_PROPERTY,
                                                  SCRIPTS_SOURCES_PROPERTY,
                                                  SCRIPTS_TARGET_PROPERTY)
from pybuilder.plugins.python.core_plugin import init_python_directories
from test_utils import patch


class InitPythonDirectoriesTest(unittest.TestCase):
    def greedy(self, generator):
        return [element for element in generator]

    def setUp(self):
        self.project = Project(".")

    @patch("pybuilder.plugins.python.core_plugin.os.listdir")
    @patch("pybuilder.plugins.python.core_plugin.os.path.isfile")
    def test_should_set_list_modules_function_with_project_modules(self, _, source_listdir):
        source_listdir.return_value = ["foo.py", "bar.py", "some-package"]

        init_python_directories(self.project)

        self.assertEqual(
            ['foo', 'bar'],
            self.greedy(self.project.list_modules())
        )

    @patch("pybuilder.plugins.python.core_plugin.os.walk")
    @patch("pybuilder.plugins.python.core_plugin.os.path.exists")
    def test_should_set_list_packages_function_with_project_packages(self, _, walk):
        walk.return_value = [(join(".", "src", "main", "python", "pybuilder"),
                              ['pluginhelper', 'plugins'],
                              ['execution.py', 'terminal.py', 'execution.pyc', 'scaffolding.py']
                              )]
        self.project.set_property("dir_source_main_python",
                                  "src/main/python")

        init_python_directories(self.project)

        self.assertEqual(
            ['pybuilder.pluginhelper',
             'pybuilder.plugins'],
            self.greedy(self.project.list_packages())
        )

    @patch("pybuilder.plugins.python.core_plugin.os.walk")
    @patch("pybuilder.plugins.python.core_plugin.os.path.exists")
    def test_should_not_cut_off_packages_when_path_ends_with_trailing_slash(self, _, walk):
        walk.return_value = [(join(".", "src", "main", "python", "pybuilder"),
                              ['pluginhelper', 'plugins'],
                              ['execution.py', 'terminal.py', 'execution.pyc', 'scaffolding.py']
                              )]
        self.project.set_property("dir_source_main_python",
                                  "src/main/python/")

        init_python_directories(self.project)

        self.assertEqual(
            ['pybuilder.pluginhelper',
             'pybuilder.plugins'],
            self.greedy(self.project.list_packages())
        )

    def test_should_set_python_sources_property(self):
        init_python_directories(self.project)
        self.assertEqual(
            "src/main/python", self.project.get_property(PYTHON_SOURCES_PROPERTY, "caboom"))

    def test_should_set_scripts_sources_property(self):
        init_python_directories(self.project)
        self.assertEqual(
            "src/main/scripts", self.project.get_property(SCRIPTS_SOURCES_PROPERTY, "caboom"))

    def test_should_set_dist_scripts_property(self):
        init_python_directories(self.project)
        self.assertEqual(
            "scripts", self.project.get_property(SCRIPTS_TARGET_PROPERTY))

    def test_should_set_dist_property(self):
        init_python_directories(self.project)
        self.assertEqual("$dir_target/dist/.-1.0.dev0",
                         self.project.get_property(DISTRIBUTION_PROPERTY, "caboom"))
