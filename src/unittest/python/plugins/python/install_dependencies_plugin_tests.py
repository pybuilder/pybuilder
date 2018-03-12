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
from os.path import normcase as nc

from pybuilder.core import (Project,
                            Logger,
                            Dependency,
                            RequirementsFile)
from pybuilder.pip_common import pip_version
from pybuilder.pip_utils import PIP_EXEC_STANZA
from pybuilder.plugins.python.install_dependencies_plugin import (initialize_install_dependencies_plugin,
                                                                  install_runtime_dependencies,
                                                                  install_build_dependencies,
                                                                  install_dependencies,
                                                                  install_dependency,
                                                                  __reload_pip_if_updated as reload_pip_if_updated)
from test_utils import Mock, ANY, patch

__author__ = "Alexander Metzner"


class InstallDependencyTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)
        initialize_install_dependencies_plugin(self.project)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_dependency_without_version(self, exec_command, get_package_version, constraint_file):
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        exec_command.assert_called_with(PIP_EXEC_STANZA +
                                        ["install"] +
                                        (["--upgrade"] if pip_version < "9.0" else
                                         ["--upgrade", "--upgrade-strategy", "only-if-needed"]) +
                                        ['-c',
                                         nc('unittest/any_target_directory/install_dependencies_constraints'),
                                         'spam'],
                                        cwd=ANY,
                                        env=ANY,
                                        error_file_name=ANY,
                                        outfile_name=ANY,
                                        shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_requirements_file_dependency(self, exec_command, get_package_version, constraint_file):
        dependency = RequirementsFile("requirements.txt")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", '-r', "requirements.txt"], ANY, env=ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_dependency_without_version_on_windows_derivate(self, exec_command, get_package_version,
                                                                           constraint_file):
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", "spam"], ANY, env=ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_common._pip_disallows_insecure_packages_by_default", return_value=True)
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_dependency_insecurely_when_property_is_set(self, exec_command, _, get_package_version,
                                                                       constraint_file):
        dependency = Dependency("spam")
        self.project.set_property("install_dependencies_insecure_installation", ["spam"])

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", "--allow-unverified", "spam", "--allow-external", "spam", 'spam'],
            ANY, env=ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_common._pip_disallows_insecure_packages_by_default", return_value=True)
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_dependency_securely_when_property_is_not_set_to_dependency(self, exec_command, _,
                                                                                       get_package_version,
                                                                                       constraint_file):
        dependency = Dependency("spam")
        self.project.set_property("install_dependencies_insecure_installation", ["some-other-dependency"])

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", "--allow-unverified", "some-other-dependency", "--allow-external",
                               "some-other-dependency", 'spam'], ANY, env=ANY, shell=False)
        #  some-other-dependency might be a dependency of 'spam'
        #  so we always have to put the insecure dependencies in the command line :-(

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_common._pip_disallows_insecure_packages_by_default", return_value=False)
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_not_use_insecure_flags_when_pip_version_is_too_low(self, exec_command, _, get_package_version,
                                                                       constraint_file):
        dependency = Dependency("spam")
        self.project.set_property("install_dependencies_insecure_installation", ["spam"])

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", 'spam'], ANY, env=ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_dependency_using_custom_index_url(self, exec_command, get_package_version,
                                                              constraint_file):
        self.project.set_property("install_dependencies_index_url", "some_index_url")
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", "--index-url", "some_index_url", 'spam'], ANY, env=ANY,
            shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_use_extra_index_url_when_index_url_is_not_set(self, exec_command, get_package_version,
                                                                  constraint_file):
        self.project.set_property("install_dependencies_extra_index_url", "some_extra_index_url")
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", "--extra-index-url", "some_extra_index_url", 'spam'], ANY,
            env=ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_use_index_and_extra_index_url_when_index_and_extra_index_url_are_set(self, exec_command,
                                                                                         get_package_version,
                                                                                         constraint_file):
        self.project.set_property("install_dependencies_index_url", "some_index_url")
        self.project.set_property("install_dependencies_extra_index_url", "some_extra_index_url")
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", "--index-url", "some_index_url", "--extra-index-url",
                               "some_extra_index_url", 'spam'], ANY, env=ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_upgrade_dependencies(self, exec_command, get_package_version, constraint_file):
        self.project.set_property("install_dependencies_upgrade", True)
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", "--upgrade", 'spam'], ANY, env=ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_dependency_with_version(self, exec_command, get_package_version, constraint_file):
        dependency = Dependency("spam", "0.1.2")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", 'spam>=0.1.2'], ANY, env=ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_dependency_with_version_and_operator(self, exec_command, get_package_version,
                                                                 constraint_file):
        dependency = Dependency("spam", "==0.1.2")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", 'spam==0.1.2'], ANY, env=ANY, shell=False)

    def test_should_install_dependency_with_wrong_version_and_operator(self):
        self.assertRaises(ValueError, Dependency, "spam", "~=1")

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_dependency_with_url(self, exec_command, get_package_version, constraint_file):
        dependency = Dependency("spam", url="some_url")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", "--force-reinstall", 'some_url'], ANY, env=ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_dependency_with_url_even_if_version_is_given(self, exec_command, get_package_version,
                                                                         constraint_file):
        dependency = Dependency("spam", version="0.1.2", url="some_url")

        install_dependency(self.logger, self.project, dependency)

        exec_command(
            PIP_EXEC_STANZA + ["install", "--force-reinstall", 'some_url'], ANY, env=ANY, shell=False)


class InstallRuntimeDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.project.set_property("dir_target", "/any_target_directory")
        self.logger = Mock(Logger)
        initialize_install_dependencies_plugin(self.project)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_multiple_dependencies(self, exec_command, get_package_version, constraint_file):
        self.project.depends_on("spam")
        self.project.depends_on("eggs")
        self.project.depends_on_requirements("requirements.txt")

        install_runtime_dependencies(self.logger, self.project)

        exec_command(PIP_EXEC_STANZA + ["install", 'spam'], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", 'eggs'], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", '-r', 'requirements.txt'], ANY, shell=False)

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_multiple_dependencies_locally(self, exec_command, get_package_version, constraint_file):
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

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_multiple_dependencies(self, exec_command, get_package_version, constraint_file):
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

    @patch("pybuilder.pip_utils.create_constraint_file")
    @patch("pybuilder.pip_utils.get_package_version", return_value={})
    @patch("pybuilder.pip_utils.execute_command", return_value=0)
    def test_should_install_single_dependency_without_version(self, exec_command, get_package_version, constraint_file):
        self.project.depends_on("spam")
        self.project.build_depends_on("eggs")

        install_dependencies(self.logger, self.project)

        exec_command(PIP_EXEC_STANZA + ["install", 'spam'], ANY, shell=False)
        exec_command(PIP_EXEC_STANZA + ["install", 'eggs'], ANY, shell=False)


class InstallDependencyPluginTest(unittest.TestCase):
    def setUp(self):
        self.logger = Mock(Logger)
        self.dependencies_to_install_with_pip = [Dependency('test'), Dependency('pip')]
        self.dependencies_to_install_without_pip = [Dependency('test'), Dependency('test2')]
        from pybuilder import pip_common, pip_utils
        self.pip_common_object = pip_common.Version("1.2.3")
        self.pip_utils_method = pip_utils.pip_install

    def test_should_reload_pip_common_if_needed(self):
        reload_pip_if_updated(self.logger, self.dependencies_to_install_with_pip)
        from pybuilder import pip_common
        self.assertFalse(isinstance(self.pip_common_object, pip_common.Version))

    def test_should_reload_pip_utils_if_needed(self):
        reload_pip_if_updated(self.logger, self.dependencies_to_install_with_pip)
        from pybuilder import pip_utils
        self.assertFalse(self.pip_utils_method == pip_utils.pip_install)

    def test_should_not_reload_pip_common(self):
        reload_pip_if_updated(self.logger, self.dependencies_to_install_without_pip)
        from pybuilder import pip_common
        self.assertTrue(isinstance(self.pip_common_object, pip_common.Version))

    def test_should_not_reload_pip_utils(self):
        reload_pip_if_updated(self.logger, self.dependencies_to_install_without_pip)
        from pybuilder import pip_utils
        self.assertTrue(self.pip_utils_method == pip_utils.pip_install)
