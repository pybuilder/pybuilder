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

from pybuilder.core import Project
from pybuilder.plugins.python.core_plugin import (DISTRIBUTION_PROPERTY,
                                                  PYTHON_SOURCES_PROPERTY,
                                                  SCRIPTS_SOURCES_PROPERTY,
                                                  SCRIPTS_TARGET_PROPERTY)
from pybuilder.plugins.python.core_plugin import init_python_directories, create_venvs
from test_utils import patch, Mock


class InitPythonDirectoriesTest(unittest.TestCase):
    def greedy(self, generator):
        return list(generator)

    def setUp(self):
        self.project = Project(".")

    @patch("pybuilder.plugins.python.core_plugin.walk")
    def test_should_set_list_modules_function_with_project_modules(self, walk):
        self.project.set_property("dir_source_main_python",
                                  "src/main/python")

        init_python_directories(self.project)
        src_path = self.project.expand_path("$dir_source_main_python")

        walk.return_value = [
            (src_path, ["pybuilder"], ("foo.py", "bar.py")),
            (join(src_path, "pybuilder"), ["pluginhelper", "plugins"], ["__init__.py", "foo.py", "foo.txt"]),
            (join(src_path, "pybuilder", "pluginhelper"), [], ["__init__.py"]),
            (join(src_path, "pybuilder", "plugins"), [], ["__init__.py"])
        ]

        self.assertEqual(
            ["bar", "foo"],
            self.greedy(self.project.list_modules())
        )

    @patch("pybuilder.plugins.python.core_plugin.walk")
    def test_should_set_list_packages_function_with_project_packages(self, walk):
        self.project.set_property("dir_source_main_python",
                                  "src/main/python")

        init_python_directories(self.project)
        src_path = self.project.expand_path("$dir_source_main_python")

        walk.return_value = [
            (join(src_path, "pybuilder"), ["pluginhelper", "plugins"], ["__init__.py", "foo.py", "foo.txt"]),
            (join(src_path, "pybuilder", "pluginhelper"), [], ["__init__.py"]),
            (join(src_path, "pybuilder", "plugins"), [], ["__init__.py"])
        ]

        self.assertEqual(
            ["pybuilder",
             "pybuilder.pluginhelper",
             "pybuilder.plugins"],
            self.greedy(self.project.list_packages())
        )

    @patch("pybuilder.plugins.python.core_plugin.walk")
    def test_should_not_cut_off_packages_when_path_ends_with_trailing_slash(self, walk):
        self.project.set_property("dir_source_main_python",
                                  "src/main/python/")

        init_python_directories(self.project)
        src_path = self.project.expand_path("$dir_source_main_python")

        walk.return_value = [
            (join(src_path, "pybuilder"), ["pluginhelper", "plugins"], ("__init__.py", "foo.py", "foo.txt")),
            (join(src_path, "pybuilder", "pluginhelper"), [], ["__init__.py"]),
            (join(src_path, "pybuilder", "plugins"), [], ["__init__.py"])
        ]

        self.assertEqual(
            ["pybuilder",
             "pybuilder.pluginhelper",
             "pybuilder.plugins"],
            self.greedy(self.project.list_packages())
        )

    @patch("pybuilder.plugins.python.core_plugin.walk")
    @patch("pybuilder.plugins.python.core_plugin.exists")
    def test_should_set_list_scripts_function_with_project_scripts(self, exists, walk):
        self.project.set_property("dir_source_main_scripts",
                                  "src/main/scripts")

        init_python_directories(self.project)
        src_path = self.project.expand_path("$dir_source_main_scripts")
        exists.return_value = True

        walk.return_value = [
            (src_path, ["pybuilder"], ("boo.py", "baz.py")),
            (join(src_path, "pybuilder"), ["pluginhelper", "plugins"], ["__init__.py", "foo.py", "foo.txt"]),
            (join(src_path, "pybuilder", "pluginhelper"), [], ["__init__.py"]),
            (join(src_path, "pybuilder", "plugins"), [], ["__init__.py"])
        ]

        self.assertEqual(
            ["baz.py", "boo.py"],
            self.greedy(self.project.list_scripts())
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


class CreateVenvsDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project(".")
        self.project.set_property("dir_target", "target")
        self.project.set_property("dir_logs", "$dir_target/logs")
        init_python_directories(self.project)

        self.project.build_depends_on("pytest", ">=8")
        self.project.build_depends_on("coverage", ">=7")
        self.project.depends_on("spam", ">=0.7")
        self.project.depends_on("eggs")
        self.project.depends_on("cryptography", ">=42", extra="security")
        self.project.depends_on("sphinx", ">=7", extra="docs")

        self.reactor = Mock()
        self.reactor.python_env_registry = {"system": Mock(is_pypy=False)}
        self.project.set_property("venv_names", [])

    def venv_dependencies(self):
        with patch("pybuilder.plugins.python.core_plugin.mkdir"):
            create_venvs(Mock(), self.project, self.reactor)
        venv_map = self.project.get_property("venv_dependencies")
        return {name: sorted(d.name for d in dependencies) for name, dependencies in venv_map.items()}

    def test_should_default_to_no_extras_in_either_venv(self):
        self.assertEqual({"build": ["coverage", "eggs", "pytest", "spam"],
                          "test": ["eggs", "spam"]},
                         self.venv_dependencies())

    def test_should_install_selected_extras_into_both_venvs(self):
        self.project.set_property("install_dependencies_extras", ["security"])

        self.assertEqual({"build": ["coverage", "cryptography", "eggs", "pytest", "spam"],
                          "test": ["cryptography", "eggs", "spam"]},
                         self.venv_dependencies())

    def test_should_install_all_extras_into_both_venvs_when_selecting_all(self):
        self.project.set_property("install_dependencies_extras", "*")

        self.assertEqual({"build": ["coverage", "cryptography", "eggs", "pytest", "spam", "sphinx"],
                          "test": ["cryptography", "eggs", "spam", "sphinx"]},
                         self.venv_dependencies())

    def test_should_leave_an_explicit_venv_dependencies_entry_alone(self):
        self.project.set_property("install_dependencies_extras", "*")
        self.project.set_property("venv_dependencies", {"test": list(self.project.base_dependencies)})

        self.assertEqual({"build": ["coverage", "cryptography", "eggs", "pytest", "spam", "sphinx"],
                          "test": ["eggs", "spam"]},
                         self.venv_dependencies())

    def test_should_declare_the_extras_selection_property(self):
        self.assertEqual([], self.project.get_property("install_dependencies_extras"))
