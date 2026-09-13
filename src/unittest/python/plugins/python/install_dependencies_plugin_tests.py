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
from pybuilder.pip_utils import PIP_MODULE_STANZA
from pybuilder.plugins.python.install_dependencies_plugin import (initialize_install_dependencies_plugin,
                                                                  install_runtime_dependencies,
                                                                  install_build_dependencies,
                                                                  install_dependencies,
                                                                  list_dependencies)
from test_utils import Mock, ANY, patch, call

__author__ = "Alexander Metzner, Arcadiy Ivanov"


class InstallRuntimeDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("install_env", "whatever")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)

        self.reactor = Mock()
        self.pyb_env = Mock()
        self.pyb_env.executable = ["a/b"]
        self.pyb_env.env_dir = "a"
        self.pyb_env.execute_command.return_value = 0
        self.reactor.python_env_registry = {"whatever": self.pyb_env}

        initialize_install_dependencies_plugin(self.project)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_multiple_dependencies(self,
                                                  *_):
        self.project.depends_on("spam")
        self.project.depends_on("eggs")
        self.project.depends_on_requirements("requirements.txt")

        install_runtime_dependencies(self.logger, self.project, self.reactor)

        exec_cmd = self.pyb_env.execute_command
        call_stanza = self.pyb_env.executable + PIP_MODULE_STANZA + ["install", "-c", ANY]
        exec_cmd.assert_called_with(call_stanza +
                                    ["eggs", "spam", "-r", "requirements.txt"],
                                    outfile_name=ANY,
                                    error_file_name=ANY,
                                    env=ANY, cwd=None, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_multiple_dependencies_locally(self,
                                                          *_):
        self.project.depends_on("spam")
        self.project.depends_on("eggs")
        self.project.depends_on("foo")
        self.project.set_property("install_dependencies_local_mapping", {
            "spam": "any-dir",
            "eggs": "any-other-dir"
        })

        install_runtime_dependencies(self.logger, self.project, self.reactor)

        exec_cmd = self.pyb_env.execute_command
        call_stanza = self.pyb_env.executable + PIP_MODULE_STANZA + ["install", "-c", ANY]

        exec_cmd.assert_has_calls([call(call_stanza + ["-t", "any-other-dir", "eggs"],
                                        outfile_name=ANY,
                                        error_file_name=ANY,
                                        env=ANY, cwd=None, shell=False, no_path_search=True),
                                   call(call_stanza + ["-t", "any-dir", "spam"],
                                        outfile_name=ANY,
                                        error_file_name=ANY,
                                        env=ANY, cwd=None, shell=False, no_path_search=True),
                                   call(call_stanza + ["foo"],
                                        outfile_name=ANY,
                                        error_file_name=ANY,
                                        env=ANY, cwd=None, shell=False, no_path_search=True)
                                   ], any_order=True)


class InstallBuildDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("install_env", "whatever")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)

        self.reactor = Mock()
        self.pyb_env = Mock()
        self.pyb_env.executable = ["a/b"]
        self.pyb_env.env_dir = "a"
        self.pyb_env.execute_command.return_value = 0
        self.reactor.python_env_registry = {"whatever": self.pyb_env}

        initialize_install_dependencies_plugin(self.project)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_multiple_dependencies(self,
                                                  *_):
        self.project.build_depends_on("spam")
        self.project.build_depends_on("eggs")
        self.project.build_depends_on_requirements("requirements-dev.txt")

        install_build_dependencies(self.logger, self.project, self.reactor)

        exec_cmd = self.pyb_env.execute_command
        call_stanza = self.pyb_env.executable + PIP_MODULE_STANZA + ["install", "-c", ANY]

        exec_cmd.assert_called_with(call_stanza +
                                    ["eggs", "spam", "-r", "requirements-dev.txt"],
                                    outfile_name=ANY,
                                    error_file_name=ANY,
                                    env=ANY, cwd=None, shell=False, no_path_search=True)


class InstallDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("install_env", "whatever")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)

        self.reactor = Mock()
        self.pyb_env = Mock()
        self.pyb_env.executable = ["a/b"]
        self.pyb_env.env_dir = "a"
        self.pyb_env.execute_command.return_value = 0
        self.reactor.python_env_registry = {"whatever": self.pyb_env}

        initialize_install_dependencies_plugin(self.project)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_single_dependency_without_version(self,
                                                              *_):
        self.project.depends_on("spam")
        self.project.build_depends_on("eggs")

        install_dependencies(self.logger, self.project, self.reactor)

        exec_cmd = self.pyb_env.execute_command
        call_stanza = self.pyb_env.executable + PIP_MODULE_STANZA + ["install", "-c", ANY]

        exec_cmd.assert_called_with(call_stanza +
                                    ["eggs", "spam"],
                                    outfile_name=ANY,
                                    error_file_name=ANY,
                                    env=ANY, cwd=None, shell=False, no_path_search=True)


class InstallDependenciesExtrasTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("install_env", "whatever")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)

        self.reactor = Mock()
        self.pyb_env = Mock()
        self.pyb_env.executable = ["a/b"]
        self.pyb_env.env_dir = "a"
        self.pyb_env.execute_command.return_value = 0
        self.pyb_env.marker_env = {"sys_platform": "linux", "python_version": "3.13"}
        self.reactor.python_env_registry = {"whatever": self.pyb_env}

        initialize_install_dependencies_plugin(self.project)

        self.project.depends_on("spam")
        self.project.depends_on("eggs")
        self.project.depends_on("cryptography", extra="security")
        self.project.depends_on("pyopenssl", extra="security")
        self.project.depends_on("sphinx", extra="docs")

    def installed_targets(self, task):
        with patch("pybuilder.install_utils.tail_log"), \
                patch("pybuilder.install_utils.open"), \
                patch("pybuilder.install_utils.create_constraint_file"), \
                patch("pybuilder.install_utils.get_packages_info", return_value={}):
            task(self.logger, self.project, self.reactor)
        return self.pyb_env.execute_command.call_args[0][0]

    def test_should_default_to_installing_no_extras(self):
        self.assertEqual([], self.project.get_property("install_dependencies_extras"))

    def test_should_not_install_extras_by_default(self):
        targets = self.installed_targets(install_runtime_dependencies)

        self.assertIn("spam", targets)
        self.assertIn("eggs", targets)
        self.assertNotIn("cryptography", targets)
        self.assertNotIn("sphinx", targets)

    def test_should_install_a_selected_extras_group_with_runtime_dependencies(self):
        self.project.set_property("install_dependencies_extras", ["security"])

        targets = self.installed_targets(install_runtime_dependencies)

        self.assertIn("cryptography", targets)
        self.assertIn("pyopenssl", targets)
        self.assertNotIn("sphinx", targets)

    def test_should_install_every_extras_group_when_selecting_all(self):
        self.project.set_property("install_dependencies_extras", "*")

        targets = self.installed_targets(install_runtime_dependencies)

        self.assertIn("cryptography", targets)
        self.assertIn("sphinx", targets)

    def test_should_install_selected_extras_alongside_build_dependencies(self):
        self.project.build_depends_on("pytest")
        self.project.set_property("install_dependencies_extras", ["security"])

        targets = self.installed_targets(install_dependencies)

        self.assertIn("pytest", targets)
        self.assertIn("cryptography", targets)
        self.assertNotIn("sphinx", targets)

    def test_should_not_install_extras_with_build_dependencies_alone(self):
        self.project.build_depends_on("pytest")
        self.project.set_property("install_dependencies_extras", ["security"])

        targets = self.installed_targets(install_build_dependencies)

        self.assertIn("pytest", targets)
        self.assertNotIn("cryptography", targets)


class ListDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        initialize_install_dependencies_plugin(self.project)

        self.project.build_depends_on("pytest", ">=8")
        self.project.depends_on("spam", ">=0.7")
        self.project.depends_on("eggs")
        self.project.depends_on("cryptography", ">=42", extra="security")
        self.project.depends_on("pyopenssl", extra="security")
        self.project.depends_on("sphinx", ">=7", extra="docs")

    def listing(self):
        with patch("pybuilder.plugins.python.install_dependencies_plugin.print") as printer:
            list_dependencies(self.project)
        return printer.call_args[0][0]

    def test_should_list_build_and_runtime_dependencies(self):
        listing = self.listing()

        self.assertIn("pytest>=8", listing)
        self.assertIn("spam>=0.7", listing)
        self.assertIn("eggs", listing)

    def test_should_list_each_extras_group_with_its_dependencies(self):
        listing = self.listing()

        self.assertIn("[docs]", listing)
        self.assertIn("sphinx>=7", listing)
        self.assertIn("[security]", listing)
        self.assertIn("cryptography>=42", listing)
        self.assertIn("pyopenssl", listing)

    def test_should_mark_extras_that_are_not_selected_for_installation(self):
        listing = self.listing()

        self.assertIn("[security] (not selected for installation)", listing)
        self.assertIn("[docs] (not selected for installation)", listing)

    def test_should_not_mark_extras_that_are_selected_for_installation(self):
        self.project.set_property("install_dependencies_extras", ["security"])

        listing = self.listing()

        self.assertIn("[security]\n", listing)
        self.assertIn("[docs] (not selected for installation)", listing)
