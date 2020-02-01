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

from pybuilder.core import (Project,
                            Logger)
from pybuilder.pip_utils import PIP_EXEC_STANZA
from pybuilder.plugins.python.install_dependencies_plugin import (initialize_install_dependencies_plugin,
                                                                  install_runtime_dependencies,
                                                                  install_build_dependencies,
                                                                  install_dependencies)
from test_utils import Mock, ANY, patch

__author__ = "Alexander Metzner, Arcadiy Ivanov"


class InstallRuntimeDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)
        initialize_install_dependencies_plugin(self.project)

    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_multiple_dependencies(self, exec_command,
                                                  get_package_version,
                                                  constraint_file,
                                                  _):
        self.project.depends_on("spam")
        self.project.depends_on("eggs")
        self.project.depends_on_requirements("requirements.txt")

        install_runtime_dependencies(self.logger, self.project)

        exec_command(PIP_EXEC_STANZA + ["install", 'spam'], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", 'eggs'], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", '-r', 'requirements.txt'], ANY, shell=False)

    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_multiple_dependencies_locally(self, exec_command,
                                                          get_package_version,
                                                          constraint_file,
                                                          _):
        self.project.depends_on("spam")
        self.project.depends_on("eggs")
        self.project.depends_on("foo")
        self.project.set_property("install_dependencies_local_mapping", {
            "spam": "any-dir",
            "eggs": "any-other-dir"
        })

        install_runtime_dependencies(self.logger, self.project)

        exec_command(PIP_EXEC_STANZA + ["install", "-t", "any-dir", 'spam'], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", "-t", "any-other-dir", 'eggs'], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", 'foo'], ANY, shell=False)


class InstallBuildDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)
        initialize_install_dependencies_plugin(self.project)

    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_multiple_dependencies(self, exec_command,
                                                  get_package_version,
                                                  constraint_file,
                                                  _):
        self.project.build_depends_on("spam")
        self.project.build_depends_on("eggs")
        self.project.build_depends_on_requirements("requirements-dev.txt")

        install_build_dependencies(self.logger, self.project)

        exec_command(PIP_EXEC_STANZA + ["install", "spam"], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", "eggs"], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", '-r', 'requirements-dev.txt'], ANY, shell=False)


class InstallDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)
        initialize_install_dependencies_plugin(self.project)

    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_single_dependency_without_version(self, exec_command,
                                                              get_packages_info,
                                                              constraint_file,
                                                              _):
        self.project.depends_on("spam")
        self.project.build_depends_on("eggs")

        install_dependencies(self.logger, self.project)

        exec_command(PIP_EXEC_STANZA + ["install", 'spam'], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", 'eggs'], ANY, shell=False)
