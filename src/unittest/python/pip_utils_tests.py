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

import os
import shutil
import tempfile
import unittest
from os.path import join as jp

from pybuilder import extern, core
from pybuilder import pip_utils
from pybuilder.pip_common import UnknownExtra, WorkingSet
from test_utils import ANY, Mock

_extern = extern

CPYTHON_MARKER_ENV = {"platform_python_implementation": "CPython",
                      "python_version": "3.13",
                      "sys_platform": "linux",
                      }
PYPY_MARKER_ENV = {"platform_python_implementation": "PyPy",
                   "python_version": "3.11",
                   "sys_platform": "linux",
                   }


def write_dist_info(site_dir, name, version, requires=(), provides_extras=()):
    dist_info = jp(site_dir, "%s-%s.dist-info" % (name, version))
    os.makedirs(dist_info)
    with open(jp(dist_info, "METADATA"), "wt") as metadata:
        metadata.write("Metadata-Version: 2.1\n")
        metadata.write("Name: %s\n" % name)
        metadata.write("Version: %s\n" % version)
        for extra in provides_extras:
            metadata.write("Provides-Extra: %s\n" % extra)
        for requirement in requires:
            metadata.write("Requires-Dist: %s\n" % requirement)
        metadata.write("\n")
    return dist_info


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

    def test_as_pip_install_target_with_markers(self):
        dep = core.Dependency("pywin32", ">=300", markers="sys_platform == 'win32'")
        self.assertEqual(["pywin32>=300; sys_platform == 'win32'"], pip_utils.as_pip_install_target([dep]))

    def test_as_pip_install_target_with_extras_and_markers(self):
        dep = core.Dependency("requests[security]", ">=2.0", markers="python_version >= '3.0'")
        result = pip_utils.as_pip_install_target([dep])
        self.assertEqual(1, len(result))
        self.assertIn("requests[security]>=2.0; python_version >= '3.0'", result[0])

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


class GetPackagesInfoTests(unittest.TestCase):
    def setUp(self):
        self.site_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.site_dir, True)

        write_dist_info(self.site_dir, "aiohttp", "3.14.1",
                        requires=["multidict>=4.5",
                                  "yarl>=1.17",
                                  'aiodns>=3.3.0; extra == "speedups"',
                                  'brotli; platform_python_implementation == "CPython" and extra == "speedups"',
                                  'brotlicffi; platform_python_implementation != "CPython" and extra == "speedups"',
                                  'sphinx; extra == "Docs Only"',
                                  ],
                        provides_extras=["speedups", "Docs Only"])
        write_dist_info(self.site_dir, "multidict", "6.0.0")
        write_dist_info(self.site_dir, "yarl", "1.18.0")

    def packages(self, marker_env=CPYTHON_MARKER_ENV):
        return pip_utils.get_packages_info([self.site_dir], marker_env=marker_env)

    def test_should_report_every_installed_distribution(self):
        # The vendor importer makes PyBuilder's own vendored distributions visible to any discovery,
        # so the result is a superset of what was installed into the entry path under test.
        packages = self.packages()

        for name in ("aiohttp", "multidict", "yarl"):
            self.assertIn(name, packages)
        self.assertEqual("3.14.1", packages["aiohttp"].version)
        self.assertEqual("6.0.0", packages["multidict"].version)

    def test_should_report_only_unconditional_requirements_as_requires(self):
        self.assertEqual(["multidict", "yarl"], sorted(self.packages()["aiohttp"].requires))

    def test_should_report_requirements_of_each_declared_extra(self):
        extra_requires = self.packages()["aiohttp"].extra_requires

        self.assertEqual(["docs_only", "speedups"], sorted(extra_requires))
        self.assertEqual(["aiodns", "brotli"], sorted(extra_requires["speedups"]))
        self.assertEqual(["sphinx"], sorted(extra_requires["docs_only"]))

    def test_should_resolve_extra_requirements_against_the_given_marker_environment(self):
        cpython = self.packages(CPYTHON_MARKER_ENV)["aiohttp"].extra_requires
        pypy = self.packages(PYPY_MARKER_ENV)["aiohttp"].extra_requires

        self.assertEqual(["aiodns", "brotli"], sorted(cpython["speedups"]))
        self.assertEqual(["aiodns", "brotlicffi"], sorted(pypy["speedups"]))

    def test_should_report_no_extras_for_a_distribution_declaring_none(self):
        self.assertEqual({}, self.packages()["multidict"].extra_requires)

    def test_should_reject_an_extra_the_distribution_does_not_provide(self):
        aiohttp = [dist for dist in WorkingSet([self.site_dir], CPYTHON_MARKER_ENV)
                   if dist.project_name == "aiohttp"][0]

        self.assertEqual(["aiodns", "brotli"], sorted(r.name for r in aiohttp.extra_requires("speedups")))
        self.assertRaises(UnknownExtra, aiohttp.extra_requires, "telemetry")
