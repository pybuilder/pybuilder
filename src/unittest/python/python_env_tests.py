#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2026 PyBuilder Team
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
from os.path import join as jp, exists

from pybuilder.plugins.python._coverage_util import (COVERAGE_PROCESS_CONFIG_ENV,
                                                     PYB_COVERAGE_PROCESS_CONFIG_ENV,
                                                     BOOTSTRAP_MODULE_NAME,
                                                     BOOTSTRAP_PTH_NAME,
                                                     BOOTSTRAP_START_NAME,
                                                     )
from pybuilder.python_env import PythonEnv, PythonEnvRegistry
from test_utils import patch, Mock

COVERAGE_ENV = {COVERAGE_PROCESS_CONFIG_ENV: "serialized-config",
                PYB_COVERAGE_PROCESS_CONFIG_ENV: "{'cov_source_path': 'src'}",
                }


class PythonEnvCoverageBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.env_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.env_dir, True)

        self.site_paths = [jp(self.env_dir, "lib", "site-packages"), jp(self.env_dir, "lib64", "site-packages")]
        for site_path in self.site_paths:
            os.makedirs(site_path)

        self.python_env = PythonEnv(self.env_dir, Mock())
        self.python_env._populated = True
        self.python_env._site_paths = tuple(self.site_paths)
        self.python_env._version = (3, 14, 1, "final", 0)
        self.python_env._environ = {"PATH": jp("usr", "bin"), "HOME": jp("home", "user")}

    def _assert_planted(self, site_path, start_file_expected=False):
        self.assertTrue(exists(jp(site_path, BOOTSTRAP_MODULE_NAME + ".py")))
        self.assertTrue(exists(jp(site_path, BOOTSTRAP_PTH_NAME)))
        self.assertEqual(exists(jp(site_path, BOOTSTRAP_START_NAME)), start_file_expected)

    def _assert_nothing_planted(self, site_path):
        self.assertFalse(exists(jp(site_path, BOOTSTRAP_MODULE_NAME + ".py")))
        self.assertFalse(exists(jp(site_path, BOOTSTRAP_PTH_NAME)))

    def test_should_plant_the_bootstrap_into_every_site_directory(self):
        self.python_env.install_coverage_bootstrap(COVERAGE_ENV)

        for site_path in self.site_paths:
            self._assert_planted(site_path)

    def test_should_plant_an_entry_point_on_python_3_15(self):
        self.python_env._version = (3, 15, 0, "final", 0)
        self.python_env.install_coverage_bootstrap(COVERAGE_ENV)

        for site_path in self.site_paths:
            self._assert_planted(site_path, start_file_expected=True)

    def test_should_carry_the_hand_off_into_the_environment_of_the_venv(self):
        self.python_env.install_coverage_bootstrap(COVERAGE_ENV)

        environ = self.python_env.environ
        for name, value in COVERAGE_ENV.items():
            self.assertEqual(environ[name], value)
        self.assertEqual(environ["HOME"], jp("home", "user"))

    def test_should_plant_the_bootstrap_when_built_during_a_covered_task(self):
        with patch.dict(os.environ, COVERAGE_ENV):
            self.python_env._install_coverage_bootstrap_if_covered()

        for site_path in self.site_paths:
            self._assert_planted(site_path)
        self.assertEqual(self.python_env.environ[COVERAGE_PROCESS_CONFIG_ENV], "serialized-config")

    def test_should_plant_nothing_when_not_built_during_a_covered_task(self):
        with patch.dict(os.environ, {"PATH": jp("usr", "bin")}, clear=True):
            self.python_env._install_coverage_bootstrap_if_covered()

        for site_path in self.site_paths:
            self._assert_nothing_planted(site_path)
        self.assertNotIn(COVERAGE_PROCESS_CONFIG_ENV, self.python_env.environ)

    def test_should_skip_site_directories_that_do_not_exist(self):
        missing = jp(self.env_dir, "lib", "no-such-site-packages")
        self.python_env._site_paths = (self.site_paths[0], missing, self.site_paths[1])

        self.python_env.install_coverage_bootstrap(COVERAGE_ENV)

        for site_path in self.site_paths:
            self._assert_planted(site_path)
        self.assertFalse(exists(missing))


class PythonEnvRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = PythonEnvRegistry(Mock())
        self.envs = {"system": Mock(name="system"), "build": Mock(name="build"), "test": Mock(name="test")}
        for name, python_env in self.envs.items():
            self.registry[name] = python_env

    def test_should_list_every_registered_environment(self):
        self.assertEqual(dict(self.registry.items()), self.envs)

    def test_should_list_an_overridden_environment_once_as_the_override(self):
        override = Mock(name="override")
        self.registry.push_override("build", override)

        self.assertEqual(dict(self.registry.items()), dict(self.envs, build=override))

    def test_should_not_list_a_deleted_environment(self):
        del self.registry["test"]

        self.assertEqual(dict(self.registry.items()), {name: python_env
                                                       for name, python_env in self.envs.items()
                                                       if name != "test"})
