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

import shutil
import sys
import tempfile
import unittest
from importlib.util import module_from_spec
from os.path import join as jp, normcase as nc

from pybuilder.plugins.python._coverage_shim import CoverageImporter

PACKAGES = ["pybuilder_coverage_shim_tests_a", "pybuilder_coverage_shim_tests_b"]


class CoverageImporterTest(unittest.TestCase):
    """Exercises the `coverage` importer without depending on `coverage` itself.

    The importer only restricts *which* names it claims in `find_spec`; loading is
    name-agnostic, so stand-in modules are used to drive the loader protocol the
    way the import machinery drives it.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        for i, package in enumerate(PACKAGES):
            with open(jp(self.tmp_dir, package + ".py"), "wt") as f:
                f.write("VALUE = %d\n" % i)
        self.importer = CoverageImporter(self.tmp_dir)

    def tearDown(self):
        for package in PACKAGES:
            sys.modules.pop(package, None)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _load(self, name):
        spec = self.importer.find_spec("coverage")
        spec.name = name
        module = module_from_spec(spec)
        self.importer.exec_module(module)
        return sys.modules[name]

    def test_should_load_module_from_coverage_parent_dir(self):
        for i, package in enumerate(PACKAGES):
            module = self._load(package)
            self.assertEqual(module.VALUE, i)

    def test_should_preserve_loaded_module_spec(self):
        for package in PACKAGES:
            module = self._load(package)
            self.assertEqual(module.__spec__.name, package)
            self.assertEqual(nc(module.__spec__.origin), nc(jp(self.tmp_dir, package + ".py")))

    def test_should_not_leave_coverage_parent_dir_on_sys_path(self):
        path = list(sys.path)
        for package in PACKAGES:
            self._load(package)
        self.assertEqual(sys.path, path)

    def test_should_only_claim_coverage(self):
        self.assertIsNotNone(self.importer.find_spec("coverage"))
        self.assertIsNone(self.importer.find_spec("coverage.control"))
        self.assertIsNone(self.importer.find_spec("unittest"))
