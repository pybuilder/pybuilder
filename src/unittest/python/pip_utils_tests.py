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

from pybuilder import extern, core
from pybuilder import pip_utils
from test_utils import ANY, Mock

_extern = extern


class PipVersionTests(unittest.TestCase):
    def test_pip_dependency_version(self):
        self.assertEqual(pip_utils.build_dependency_version_string(core.Dependency("test", "1.2.3")), ">=1.2.3")
        self.assertEqual(pip_utils.build_dependency_version_string(core.Dependency("test", ">=1.2.3,<=2.3.4")),
                         "<=2.3.4,>=1.2.3")
        self.assertEqual(pip_utils.build_dependency_version_string("1.2.3"), "1.2.3")
        self.assertEqual(pip_utils.build_dependency_version_string(None), "")

    def test_version_satisfies_spec(self):
        self.assertEqual(pip_utils.version_satisfies_spec(None, "blah"), True)
        self.assertEqual(pip_utils.version_satisfies_spec("blah", None), False)
        self.assertEqual(pip_utils.version_satisfies_spec(">=1.2.3", "1.2.4"), True)
        self.assertEqual(pip_utils.version_satisfies_spec(">=1.2.3", "1.2.4.dev987"), False)
        self.assertEqual(pip_utils.version_satisfies_spec(">=1.0", "1.1.dev1"), False)
        self.assertEqual(pip_utils.version_satisfies_spec(">=1.0,>=0.0.dev0", "1.1.dev1"), True)

    def test_get_package_version(self):
        # Single item
        self.assertTrue(pip_utils.version_satisfies_spec(">=7.0", pip_utils.get_package_version("pip")["pip"]))
        self.assertTrue(
            "this package does not exist" not in pip_utils.get_package_version("this package does not exist"))
        self.assertTrue("blah" not in pip_utils.get_package_version(core.RequirementsFile("blah")))
        self.assertTrue("blah" not in pip_utils.get_package_version(core.Dependency("blah", url="fake url")))

        # Multiple different items
        multiple_different_items = pip_utils.get_package_version(
            ["pip", core.Dependency("setuptools"), core.RequirementsFile("blah")])
        self.assertTrue("pip" in multiple_different_items)
        self.assertTrue("blah" not in multiple_different_items)

        # Multiple identical items
        multiple_identical_items = pip_utils.get_package_version(
            ["pip", core.Dependency("pip")])
        self.assertTrue("pip" in multiple_identical_items)
        self.assertEqual(len(multiple_identical_items), 1)

        # Validate case
        lower_case_packages = pip_utils.get_package_version("PiP")
        self.assertTrue("pip" in lower_case_packages)
        self.assertTrue("pIp" not in lower_case_packages)
        self.assertTrue("PiP" not in lower_case_packages)

    def test_build_pip_install_options(self):
        self.assertEqual(pip_utils.build_pip_install_options(), [])
        self.assertEqual(pip_utils.build_pip_install_options(index_url="foo"), ["--index-url", "foo"])
        self.assertEqual(pip_utils.build_pip_install_options(extra_index_url="foo"), ["--extra-index-url", "foo"])
        self.assertEqual(pip_utils.build_pip_install_options(index_url="foo", extra_index_url="bar"),
                         ["--index-url", "foo", "--extra-index-url", "bar"])
        self.assertEqual(pip_utils.build_pip_install_options(extra_index_url=("foo", "bar")),
                         ["--extra-index-url", "foo", "--extra-index-url", "bar"])
        self.assertEqual(pip_utils.build_pip_install_options(trusted_host="foo"),
                         ["--trusted-host", "foo"])
        self.assertEqual(pip_utils.build_pip_install_options(trusted_host=("foo", "bar")),
                         ["--trusted-host", "foo", "--trusted-host", "bar"])
        self.assertEqual(pip_utils.build_pip_install_options(upgrade=True),
                         ["--upgrade", "--upgrade-strategy", "only-if-needed"])
        self.assertEqual(pip_utils.build_pip_install_options(upgrade=True, eager_upgrade=True),
                         ["--upgrade", "--upgrade-strategy", "eager"])
        self.assertEqual(pip_utils.build_pip_install_options(verbose=True), ["-v"])
        self.assertEqual(pip_utils.build_pip_install_options(verbose=1), ["-v"])
        self.assertEqual(pip_utils.build_pip_install_options(verbose=2), ["-vv"])
        self.assertEqual(pip_utils.build_pip_install_options(verbose=3), ["-vvv"])
        self.assertEqual(pip_utils.build_pip_install_options(verbose=4), ["-vvv"])
        self.assertEqual(pip_utils.build_pip_install_options(force_reinstall=True), ["--force-reinstall"])
        self.assertEqual(pip_utils.build_pip_install_options(target_dir="target dir"), ["-t", "target dir"])
        self.assertEqual(pip_utils.build_pip_install_options(target_dir="target dir"), ["-t", "target dir"])
        self.assertEqual(pip_utils.build_pip_install_options(constraint_file="constraint file"),
                         ["-c", "constraint file"])
        self.assertEqual(pip_utils.build_pip_install_options(insecure_installs=["foo", "bar"]), [
            "--allow-unverified", "foo",
            "--allow-external", "foo",
            "--allow-unverified", "bar",
            "--allow-external", "bar"
        ])


class PipUtilsTests(unittest.TestCase):

    def test_as_constraint_target(self):
        dep = core.Dependency("abc[extra]", ">=1.2.3")
        self.assertEqual(["abc>=1.2.3"], pip_utils.as_constraints_target([dep]))

    def test_as_pip_install_target(self):
        dep = core.Dependency("abc[extra1,extra2]", ">=1.2.3")
        try:
            self.assertEqual(["abc[extra1,extra2]>=1.2.3"], pip_utils.as_pip_install_target([dep]))
        except AssertionError:
            self.assertEqual(["abc[extra2,extra1]>=1.2.3"], pip_utils.as_pip_install_target([dep]))

    def test_pip_install_environ_inherited(self):
        python_env = Mock()
        python_env.executable = []
        python_env.environ = {}
        pip_utils.pip_install("blah", python_env)
        python_env.execute_command.assert_called_once_with(ANY, cwd=None, env=python_env.environ,
                                                           error_file_name=None,
                                                           outfile_name=None,
                                                           shell=False, no_path_search=True)

    def test_pip_install_environ_overwritten(self):
        env_dict = {"a": "b"}
        python_env = Mock()
        python_env.executable = []
        python_env.environ = {}
        pip_utils.pip_install("blah", python_env, env=env_dict)
        python_env.execute_command.assert_called_once_with(ANY, cwd=None, env=env_dict, error_file_name=None,
                                                           outfile_name=None,
                                                           shell=False, no_path_search=True)
