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

from mock import patch

from pybuilder import core
from pybuilder import pip_utils


class PipVersionTests(unittest.TestCase):
    def test_pip_dependency_version(self):
        self.assertEquals(pip_utils.build_dependency_version_string(core.Dependency("test", "1.2.3")), ">=1.2.3")
        self.assertEquals(pip_utils.build_dependency_version_string(core.Dependency("test", ">=1.2.3,<=2.3.4")),
                          "<=2.3.4,>=1.2.3")
        self.assertEquals(pip_utils.build_dependency_version_string("1.2.3"), ">=1.2.3")
        self.assertEquals(pip_utils.build_dependency_version_string(">=1.2.3,<=2.3.4"), "<=2.3.4,>=1.2.3")
        self.assertRaises(ValueError, pip_utils.build_dependency_version_string, "bogus")

    def test_version_satisfies_spec(self):
        self.assertEquals(pip_utils.version_satisfies_spec(None, "blah"), True)
        self.assertEquals(pip_utils.version_satisfies_spec("blah", None), False)
        self.assertEquals(pip_utils.version_satisfies_spec(">=1.2.3", "1.2.4"), True)
        self.assertEquals(pip_utils.version_satisfies_spec(">=1.2.3", "1.2.4.dev987"), False)
        self.assertEquals(pip_utils.version_satisfies_spec(">=1.0", "1.1.dev1"), False)
        self.assertEquals(pip_utils.version_satisfies_spec(">=1.0,>=0.0.dev0", "1.1.dev1"), True)

    def test_get_package_version(self):
        self.assertTrue(pip_utils.version_satisfies_spec(">=7.0", pip_utils.get_package_version(["pip"])))
        self.assertTrue(pip_utils.get_package_version(["this package does not exist"]) is None)
        self.assertTrue(pip_utils.get_package_version(core.RequirementsFile("blah")) is None)
        self.assertTrue(pip_utils.get_package_version(core.Dependency("blah", url="fake url")) is None)

    @patch("pybuilder.pip_utils.search_packages_info")
    def test_get_package_version_name_ambiguous(self, search_packages_info):
        search_packages_info.return_value = [{"name": "foo", "version": "1.2"},
                                             {"name": "another foo", "version": "1.3"}]
        self.assertRaises(ValueError, pip_utils.get_package_version, "foo")

    def test_build_pip_install_options(self):
        self.assertEquals(pip_utils.build_pip_install_options(), [])
        self.assertEquals(pip_utils.build_pip_install_options(index_url="foo"), ["--index-url", "foo"])
        self.assertEquals(pip_utils.build_pip_install_options(extra_index_url="foo"), [])
        self.assertEquals(pip_utils.build_pip_install_options(index_url="foo", extra_index_url="bar"),
                          ["--index-url", "foo", "--extra-index-url", "bar"])
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
