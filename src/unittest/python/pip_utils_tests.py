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

import os
import unittest

from test_utils import patch, ANY

from pybuilder import core
from pybuilder import pip_utils


class PipVersionTests(unittest.TestCase):
    def test_pip_dependency_version(self):
        self.assertEquals(pip_utils.build_dependency_version_string(core.Dependency("test", "1.2.3")), ">=1.2.3")
        self.assertEquals(pip_utils.build_dependency_version_string(core.Dependency("test", ">=1.2.3,<=2.3.4")),
                          "<=2.3.4,>=1.2.3")
        self.assertEquals(pip_utils.build_dependency_version_string("1.2.3"), "1.2.3")
        self.assertEquals(pip_utils.build_dependency_version_string(None), "")

    def test_version_satisfies_spec(self):
        self.assertEquals(pip_utils.version_satisfies_spec(None, "blah"), True)
        self.assertEquals(pip_utils.version_satisfies_spec("blah", None), False)
        self.assertEquals(pip_utils.version_satisfies_spec(">=1.2.3", "1.2.4"), True)
        self.assertEquals(pip_utils.version_satisfies_spec(">=1.2.3", "1.2.4.dev987"), False)
        self.assertEquals(pip_utils.version_satisfies_spec(">=1.0", "1.1.dev1"), False)
        self.assertEquals(pip_utils.version_satisfies_spec(">=1.0,>=0.0.dev0", "1.1.dev1"), True)

    def test_get_package_version(self):
        # Single item
        self.assertTrue(pip_utils.version_satisfies_spec(">=7.0", pip_utils.get_package_version("pip")["pip"]))
        self.assertTrue(
            "this package does not exist" not in pip_utils.get_package_version("this package does not exist"))
        self.assertTrue("blah" not in pip_utils.get_package_version(core.RequirementsFile("blah")))
        self.assertTrue("blah" not in pip_utils.get_package_version(core.Dependency("blah", url="fake url")))

        # Multiple different items
        multiple_different_items = pip_utils.get_package_version(
            ["pip", core.Dependency("wheel"), core.RequirementsFile("blah")])
        self.assertTrue("pip" in multiple_different_items)
        self.assertTrue("wheel" in multiple_different_items)
        self.assertTrue("blah" not in multiple_different_items)

        # Multiple identical items
        multiple_identical_items = pip_utils.get_package_version(
            ["pip", core.Dependency("pip")])
        self.assertTrue("pip" in multiple_identical_items)
        self.assertEquals(len(multiple_identical_items), 1)

        # Validate case
        lower_case_packages = pip_utils.get_package_version("PiP")
        self.assertTrue("pip" in lower_case_packages)
        self.assertTrue("pIp" not in lower_case_packages)
        self.assertTrue("PiP" not in lower_case_packages)

    def test_build_pip_install_options(self):
        self.assertEquals(pip_utils.build_pip_install_options(), [])
        self.assertEquals(pip_utils.build_pip_install_options(index_url="foo"), ["--index-url", "foo"])
        self.assertEquals(pip_utils.build_pip_install_options(extra_index_url="foo"), ["--extra-index-url", "foo"])
        self.assertEquals(pip_utils.build_pip_install_options(index_url="foo", extra_index_url="bar"),
                          ["--index-url", "foo", "--extra-index-url", "bar"])
        self.assertEquals(pip_utils.build_pip_install_options(extra_index_url=("foo", "bar")),
                          ["--extra-index-url", "foo", "--extra-index-url", "bar"])
        self.assertEquals(pip_utils.build_pip_install_options(trusted_host="foo"),
                          ["--trusted-host", "foo"])
        self.assertEquals(pip_utils.build_pip_install_options(trusted_host=("foo", "bar")),
                          ["--trusted-host", "foo", "--trusted-host", "bar"])
        self.assertEquals(pip_utils.build_pip_install_options(upgrade=True), ["--upgrade"])
        self.assertEquals(pip_utils.build_pip_install_options(verbose=True), ["--verbose"])
        self.assertEquals(pip_utils.build_pip_install_options(force_reinstall=True), ["--force-reinstall"])
        self.assertEquals(pip_utils.build_pip_install_options(target_dir="target dir"), ["-t", "target dir"])
        self.assertEquals(pip_utils.build_pip_install_options(target_dir="target dir"), ["-t", "target dir"])
        self.assertEquals(pip_utils.build_pip_install_options(insecure_installs=["foo", "bar"]), [
            "--allow-unverified", "foo",
            "--allow-external", "foo",
            "--allow-unverified", "bar",
            "--allow-external", "bar"
        ])


class PipUtilsTests(unittest.TestCase):
    @patch("pybuilder.pip_utils.execute_command")
    def test_pip_install_environ_inherited(self, execute_command):
        pip_utils.pip_install("blah")
        execute_command.assert_called_once_with(ANY, cwd=None, env=os.environ, error_file_name=None, outfile_name=None,
                                                shell=False)

    @patch("pybuilder.pip_utils.execute_command")
    def test_pip_install_environ_overwritten(self, execute_command):
        env_dict = dict()
        pip_utils.pip_install("blah", env=env_dict)
        execute_command.assert_called_once_with(ANY, cwd=None, env=env_dict, error_file_name=None, outfile_name=None,
                                                shell=False)
