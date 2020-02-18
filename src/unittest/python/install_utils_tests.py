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
from os.path import normcase as nc, join as jp

from pybuilder.core import (Project,
                            Logger,
                            Dependency,
                            RequirementsFile)
from pybuilder.install_utils import install_dependencies
from pybuilder.pip_utils import PIP_MODULE_STANZA
from pybuilder.plugins.python.install_dependencies_plugin import initialize_install_dependencies_plugin
from test_utils import Mock, ANY, patch

__author__ = "Arcadiy Ivanov"


class InstallDependencyTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)

        self.pyb_env = Mock()
        self.pyb_env.executable = ["exec"]
        self.pyb_env.site_paths = []
        self.pyb_env.env_dir = "a"
        self.pyb_env.execute_command.return_value = 0

        initialize_install_dependencies_plugin(self.project)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_requirements_file_dependency(self, *_):
        dependency = RequirementsFile("requirements.txt")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "-r", "requirements.txt"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_dependency_without_version(self, *_):
        dependency = Dependency("spam")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch",
                             constraints_file_name="constraint_file")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "-c", nc(jp(self.pyb_env.env_dir, "constraint_file")), "spam"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_dependency_without_version_on_windows_derivate(self, *_):
        dependency = Dependency("spam")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA + ["install", "spam"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_dependency_insecurely_when_property_is_set(self, *_):
        dependency = Dependency("spam")
        self.project.set_property("install_dependencies_insecure_installation", ["spam"])

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "--allow-unverified", "spam", "--allow-external", "spam", "spam"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_dependency_securely_when_property_is_not_set_to_dependency(self, *_):
        dependency = Dependency("spam")
        self.project.set_property("install_dependencies_insecure_installation", ["some-other-dependency"])

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch",
                             constraints_file_name="constraint_file")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "-c", ANY, "--allow-unverified", "some-other-dependency",
             "--allow-external", "some-other-dependency", "spam"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)
        #  some-other-dependency might be a dependency of "spam"
        #  so we always have to put the insecure dependencies in the command line :-(

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_dependency_using_custom_index_url(self, *_):
        self.project.set_property("install_dependencies_index_url", "some_index_url")
        dependency = Dependency("spam")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "--index-url", "some_index_url", "spam"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_use_extra_index_url_when_index_url_is_not_set(self, *_):
        self.project.set_property("install_dependencies_extra_index_url", "some_extra_index_url")
        dependency = Dependency("spam")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "--extra-index-url", "some_extra_index_url", "spam"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_use_index_and_extra_index_url_when_index_and_extra_index_url_are_set(self, *_):
        self.project.set_property("install_dependencies_index_url", "some_index_url")
        self.project.set_property("install_dependencies_extra_index_url", "some_extra_index_url")
        dependency = Dependency("spam")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "--index-url", "some_index_url", "--extra-index-url", "some_extra_index_url", "spam"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_dependency_with_version(self, *_):
        dependency = Dependency("spam", "0.1.2")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "spam>=0.1.2"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_dependency_with_version_and_operator(self, *_):
        dependency = Dependency("spam", "==0.1.2")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA + ["install", "spam==0.1.2"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    def test_should_install_dependency_with_wrong_version_and_operator(self):
        self.assertRaises(ValueError, Dependency, "spam", "~=1")

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_dependency_with_url(self, *_):
        dependency = Dependency("spam", url="some_url")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "--force-reinstall", "some_url"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.install_utils.tail_log")
    @patch("pybuilder.install_utils.open")
    @patch("pybuilder.install_utils.create_constraint_file")
    @patch("pybuilder.install_utils.get_packages_info", return_value={})
    def test_should_install_dependency_with_url_even_if_version_is_given(self, *_):
        dependency = Dependency("spam", version="0.1.2", url="some_url")

        install_dependencies(self.logger, self.project, dependency, self.pyb_env, "install_batch")

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "--force-reinstall", "some_url"],
            cwd=ANY, env=ANY, error_file_name=ANY, outfile_name=ANY, shell=False, no_path_search=True)
