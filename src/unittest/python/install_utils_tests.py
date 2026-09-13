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
from pybuilder.errors import BuildFailedException
from pybuilder.install_utils import install_dependencies
from pybuilder.pip_utils import PIP_MODULE_STANZA, _PackageInfo
from pybuilder.plugins.python.install_dependencies_plugin import initialize_install_dependencies_plugin
from test_utils import Mock, ANY, patch

__author__ = "Arcadiy Ivanov"

LINUX_MARKER_ENV = {"sys_platform": "linux",
                    "os_name": "posix",
                    "platform_system": "Linux",
                    "python_version": "3.13",
                    "platform_python_implementation": "CPython",
                    }


def installed(name, version, requires=(), extra_requires=None):
    return _PackageInfo(name, version, "/any_location", list(requires), dict(extra_requires or {}))


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
        self.pyb_env.marker_env = dict(LINUX_MARKER_ENV)

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


class MarkerFilteringTest(unittest.TestCase):
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
        self.pyb_env.marker_env = dict(LINUX_MARKER_ENV)

        initialize_install_dependencies_plugin(self.project)

    def install(self, dependencies, constraint_file=None, package_type="dependency"):
        with patch("pybuilder.install_utils.tail_log"), \
                patch("pybuilder.install_utils.open"), \
                patch("pybuilder.install_utils.create_constraint_file") as create_constraints, \
                patch("pybuilder.install_utils.get_packages_info", return_value=self.installed_packages):
            installed_deps = install_dependencies(self.logger, self.project, dependencies, self.pyb_env,
                                                  "install_batch",
                                                  constraints_file_name=constraint_file,
                                                  package_type=package_type)
        self.create_constraints = create_constraints
        return installed_deps

    installed_packages = {}

    def installed_names(self, dependencies, **kwargs):
        return [d.name for d in self.install(dependencies, **kwargs)]

    def test_should_install_dependency_whose_markers_apply(self):
        dependencies = [Dependency("spam", "==1.0", markers="sys_platform == 'linux'"),
                        Dependency("eggs", "==2.0", markers="python_version >= '3.10'")]

        self.assertEqual(["spam", "eggs"], self.installed_names(dependencies))

    def test_should_not_install_dependency_whose_markers_do_not_apply(self):
        dependencies = [Dependency("spam", "==1.0", markers="sys_platform == 'win32'"),
                        Dependency("eggs", "==2.0", markers="sys_platform == 'linux'")]

        self.assertEqual(["eggs"], self.installed_names(dependencies))

    def test_should_install_the_applicable_one_of_a_conditional_pair(self):
        dependencies = [Dependency("spam", "==1.0", markers="python_version < '3.12'"),
                        Dependency("spam", "==2.0", markers="python_version >= '3.12'")]

        installed_deps = self.install(dependencies)

        self.assertEqual(["spam"], [d.name for d in installed_deps])
        self.assertEqual("==2.0", installed_deps[0].version)

    def test_should_keep_inapplicable_dependencies_out_of_the_constraints_file(self):
        dependencies = [Dependency("spam", "==1.0", markers="python_version < '3.12'"),
                        Dependency("spam", "==2.0", markers="python_version >= '3.12'"),
                        Dependency("eggs", "==3.0")]

        self.install(dependencies, constraint_file="constraint_file")

        constraints = self.create_constraints.call_args[0][1]
        self.assertEqual([("spam", "==2.0"), ("eggs", "==3.0")], [(d.name, d.version) for d in constraints])

    def test_should_bind_extra_when_evaluating_an_extras_group_dependency(self):
        dependencies = [Dependency("spam", "==1.0", extra="security", markers="extra == 'security'"),
                        Dependency("eggs", "==2.0", extra="security", markers="extra == 'docs'")]

        self.assertEqual(["spam"], self.installed_names(dependencies))

    def test_should_collapse_exact_duplicates(self):
        dependencies = [Dependency("spam", "==1.0"),
                        Dependency("spam", "==1.0"),
                        Dependency("eggs", "==2.0")]

        self.assertEqual(["spam", "eggs"], self.installed_names(dependencies))

    def test_should_fail_on_a_conflict_between_a_dependency_and_an_extra(self):
        dependencies = [Dependency("spam", "==1.0"),
                        Dependency("spam", "==2.0", extra="security")]

        self.assertRaisesRegex(BuildFailedException,
                               r"Dependency 'spam==1.0' conflicts with extra 'security' "
                               r"dependency 'spam==2.0' in this environment",
                               self.install, dependencies)

    def test_should_fail_on_a_conflict_between_two_dependencies(self):
        dependencies = [Dependency("spam", "==1.0"),
                        Dependency("spam", "==2.0")]

        self.assertRaisesRegex(BuildFailedException,
                               r"Dependency 'spam==1.0' conflicts with dependency "
                               r"'spam==2.0' in this environment",
                               self.install, dependencies)

    def test_should_name_a_conflict_after_the_kind_of_package_being_installed(self):
        dependencies = [Dependency("spam", "==1.0"),
                        Dependency("spam", "==2.0")]

        self.assertRaisesRegex(BuildFailedException,
                               r"Plugin 'spam==1.0' conflicts with plugin 'spam==2.0' in this environment",
                               self.install, dependencies, package_type="plugin")

    def test_should_not_fail_when_an_extra_merely_tightens_a_runtime_dependency(self):
        dependencies = [Dependency("spam", ">=1.0"),
                        Dependency("spam", ">=2.0", extra="security")]

        self.assertEqual(["spam", "spam"], self.installed_names(dependencies))

    def test_should_not_fail_when_conflicting_dependencies_cannot_both_apply(self):
        dependencies = [Dependency("spam", "==1.0", markers="sys_platform == 'win32'"),
                        Dependency("spam", "==2.0", extra="security")]

        self.assertEqual(["spam"], self.installed_names(dependencies))


class ExtrasSkipLogicTest(unittest.TestCase):
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
        self.pyb_env.marker_env = dict(LINUX_MARKER_ENV)

        initialize_install_dependencies_plugin(self.project)

        self.installed_packages = {
            "aiohttp": installed("aiohttp", "3.14.1",
                                 requires=["multidict", "yarl"],
                                 extra_requires={"speedups": ["aiodns", "brotli"],
                                                 "docs": ["sphinx", "myst-parser"]}),
            "multidict": installed("multidict", "6.0.0"),
            "yarl": installed("yarl", "1.18.0"),
        }

    def install(self, dependencies):
        with patch("pybuilder.install_utils.tail_log"), \
                patch("pybuilder.install_utils.open"), \
                patch("pybuilder.install_utils.create_constraint_file"), \
                patch("pybuilder.install_utils.get_packages_info", return_value=self.installed_packages):
            return [d.name for d in install_dependencies(self.logger, self.project, dependencies, self.pyb_env,
                                                         "install_batch")]

    def test_should_skip_a_satisfied_dependency_without_extras(self):
        dependencies = [Dependency("aiohttp", "==3.14.1"), Dependency("multidict", "==6.0.0")]

        self.assertEqual([], self.install(dependencies))

    def test_should_install_extras_bearing_dependency_when_the_extra_is_unsatisfied(self):
        dependencies = [Dependency("aiohttp[speedups]", "==3.14.1"), Dependency("multidict", "==6.0.0")]

        self.assertEqual(["aiohttp"], self.install(dependencies))

    def test_should_skip_extras_bearing_dependency_when_the_extra_is_satisfied(self):
        self.installed_packages["aiodns"] = installed("aiodns", "3.3.0")
        self.installed_packages["brotli"] = installed("brotli", "1.1.0")
        dependencies = [Dependency("aiohttp[speedups]", "==3.14.1"), Dependency("multidict", "==6.0.0")]

        self.assertEqual([], self.install(dependencies))

    def test_should_install_when_only_some_of_the_extras_requirements_are_present(self):
        self.installed_packages["aiodns"] = installed("aiodns", "3.3.0")
        dependencies = [Dependency("aiohttp[speedups]", "==3.14.1"), Dependency("multidict", "==6.0.0")]

        self.assertEqual(["aiohttp"], self.install(dependencies))

    def test_should_require_every_requested_extra_to_be_satisfied(self):
        self.installed_packages["aiodns"] = installed("aiodns", "3.3.0")
        self.installed_packages["brotli"] = installed("brotli", "1.1.0")
        dependencies = [Dependency("aiohttp[speedups,docs]", "==3.14.1"), Dependency("multidict", "==6.0.0")]

        self.assertEqual(["aiohttp"], self.install(dependencies))

    def test_should_install_when_the_installed_package_does_not_provide_the_extra(self):
        dependencies = [Dependency("aiohttp[telemetry]", "==3.14.1"), Dependency("multidict", "==6.0.0")]

        self.assertEqual(["aiohttp"], self.install(dependencies))
        self.logger.warn.assert_called_once_with(
            "Package '%s' does not provide extra '%s' and cannot be verified as installed; "
            "it will be handed to pip", "aiohttp", "telemetry")
