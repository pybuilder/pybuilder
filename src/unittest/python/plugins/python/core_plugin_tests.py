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

import unittest
from os.path import join

from test_utils import patch

from pybuilder.core import Project
from pybuilder.plugins.python.core_plugin import (
    DISTRIBUTION_PROPERTY,
    PYTHON_SOURCES_PROPERTY,
    SCRIPTS_SOURCES_PROPERTY,
    SCRIPTS_TARGET_PROPERTY,
    init_python_directories,
)


class InitPythonDirectoriesTest(unittest.TestCase):
    def greedy(self, generator):
        return list(generator)

    def setUp(self):
        self.project = Project(".")

    @patch("pybuilder.plugins.python.core_plugin.walk")
    def test_should_set_list_modules_function_with_project_modules(self, walk):
        self.project.set_property("dir_source_main_python", "src/main/python")

        init_python_directories(self.project)
        src_path = self.project.expand_path("$dir_source_main_python")

        walk.return_value = [
            (src_path, ["pybuilder"], ("foo.py", "bar.py")),
            (
                join(src_path, "pybuilder"),
                ["pluginhelper", "plugins"],
                ["__init__.py", "foo.py", "foo.txt"],
            ),
            (join(src_path, "pybuilder", "pluginhelper"), [], ["__init__.py"]),
            (join(src_path, "pybuilder", "plugins"), [], ["__init__.py"]),
        ]

        self.assertEqual(["bar", "foo"], self.greedy(self.project.list_modules()))

    @patch("pybuilder.plugins.python.core_plugin.walk")
    def test_should_set_list_packages_function_with_project_packages(self, walk):
        self.project.set_property("dir_source_main_python", "src/main/python")

        init_python_directories(self.project)
        src_path = self.project.expand_path("$dir_source_main_python")

        walk.return_value = [
            (
                join(src_path, "pybuilder"),
                ["pluginhelper", "plugins"],
                ["__init__.py", "foo.py", "foo.txt"],
            ),
            (join(src_path, "pybuilder", "pluginhelper"), [], ["__init__.py"]),
            (join(src_path, "pybuilder", "plugins"), [], ["__init__.py"]),
        ]

        self.assertEqual(
            ["pybuilder", "pybuilder.pluginhelper", "pybuilder.plugins"],
            self.greedy(self.project.list_packages()),
        )

    @patch("pybuilder.plugins.python.core_plugin.walk")
    def test_should_not_cut_off_packages_when_path_ends_with_trailing_slash(self, walk):
        self.project.set_property("dir_source_main_python", "src/main/python/")

        init_python_directories(self.project)
        src_path = self.project.expand_path("$dir_source_main_python")

        walk.return_value = [
            (
                join(src_path, "pybuilder"),
                ["pluginhelper", "plugins"],
                ("__init__.py", "foo.py", "foo.txt"),
            ),
            (join(src_path, "pybuilder", "pluginhelper"), [], ["__init__.py"]),
            (join(src_path, "pybuilder", "plugins"), [], ["__init__.py"]),
        ]

        self.assertEqual(
            ["pybuilder", "pybuilder.pluginhelper", "pybuilder.plugins"],
            self.greedy(self.project.list_packages()),
        )

    @patch("pybuilder.plugins.python.core_plugin.walk")
    @patch("pybuilder.plugins.python.core_plugin.exists")
    def test_should_set_list_scripts_function_with_project_scripts(self, exists, walk):
        self.project.set_property("dir_source_main_scripts", "src/main/scripts")

        init_python_directories(self.project)
        src_path = self.project.expand_path("$dir_source_main_scripts")
        exists.return_value = True

        walk.return_value = [
            (src_path, ["pybuilder"], ("boo.py", "baz.py")),
            (
                join(src_path, "pybuilder"),
                ["pluginhelper", "plugins"],
                ["__init__.py", "foo.py", "foo.txt"],
            ),
            (join(src_path, "pybuilder", "pluginhelper"), [], ["__init__.py"]),
            (join(src_path, "pybuilder", "plugins"), [], ["__init__.py"]),
        ]

        self.assertEqual(["baz.py", "boo.py"], self.greedy(self.project.list_scripts()))

    def test_should_set_python_sources_property(self):
        init_python_directories(self.project)
        self.assertEqual(
            "src/main/python",
            self.project.get_property(PYTHON_SOURCES_PROPERTY, "caboom"),
        )

    def test_should_set_scripts_sources_property(self):
        init_python_directories(self.project)
        self.assertEqual(
            "src/main/scripts",
            self.project.get_property(SCRIPTS_SOURCES_PROPERTY, "caboom"),
        )

    def test_should_set_dist_scripts_property(self):
        init_python_directories(self.project)
        self.assertEqual("scripts", self.project.get_property(SCRIPTS_TARGET_PROPERTY))

    def test_should_set_dist_property(self):
        init_python_directories(self.project)
        self.assertEqual(
            "$dir_target/dist/.-1.0.dev0",
            self.project.get_property(DISTRIBUTION_PROPERTY, "caboom"),
        )
