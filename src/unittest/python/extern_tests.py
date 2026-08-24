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

import importlib.resources
import shutil
import sys
import tempfile
import unittest
from os import makedirs
from os.path import join as jp, normcase as nc

from pybuilder.extern import VendorImporter

VENDOR_PKG = "pybuilder_extern_tests_vendor"
ALIASES = ["alpha", "beta"]


class VendorImporterTest(unittest.TestCase):
    """Exercises the vendored-package alias importer end-to-end.

    The vendored packages are created on the fly so that the test does not depend
    on what happens to be vendored into `pybuilder._vendor` at any point in time.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        for alias in ALIASES:
            pkg_dir = jp(self.tmp_dir, VENDOR_PKG, alias)
            makedirs(pkg_dir)
            with open(jp(pkg_dir, "__init__.py"), "wt") as f:
                f.write("from .sub import VALUE\n")
            with open(jp(pkg_dir, "sub.py"), "wt") as f:
                f.write("VALUE = %r\n" % alias)
            with open(jp(pkg_dir, "data.txt"), "wt") as f:
                f.write(alias)
        with open(jp(self.tmp_dir, VENDOR_PKG, "__init__.py"), "wt") as f:
            f.write("")

        sys.path.insert(0, self.tmp_dir)
        self.importer = VendorImporter(__name__, ALIASES, VENDOR_PKG)
        self.importer.install()

    def tearDown(self):
        sys.meta_path.remove(self.importer)
        sys.path.remove(self.tmp_dir)
        for name in list(sys.modules):
            if name == VENDOR_PKG or name.startswith(VENDOR_PKG + "."):
                del sys.modules[name]
            for alias in ALIASES:
                if name == alias or name.startswith(alias + "."):
                    del sys.modules[name]
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_should_alias_vendored_packages(self):
        for alias in ALIASES:
            module = __import__(alias)
            self.assertEqual(module.VALUE, alias)
            self.assertIs(module, sys.modules["%s.%s" % (VENDOR_PKG, alias)])

    def test_should_alias_vendored_submodules(self):
        for alias in ALIASES:
            module = __import__("%s.sub" % alias, fromlist=["VALUE"])
            self.assertEqual(module.VALUE, alias)
            self.assertIs(module, sys.modules["%s.%s.sub" % (VENDOR_PKG, alias)])

    def test_should_preserve_vendored_module_spec(self):
        for alias in ALIASES:
            module = __import__(alias)
            spec = module.__spec__
            self.assertEqual(spec.name, "%s.%s" % (VENDOR_PKG, alias))
            self.assertEqual(nc(spec.origin),
                             nc(jp(self.tmp_dir, VENDOR_PKG, alias, "__init__.py")))
            self.assertEqual([nc(p) for p in spec.submodule_search_locations],
                             [nc(jp(self.tmp_dir, VENDOR_PKG, alias))])

    def test_should_locate_resources_of_aliased_packages(self):
        for alias in ALIASES:
            __import__(alias)
            resource = importlib.resources.files(alias) / "data.txt"
            self.assertEqual(resource.read_text(), alias)

    def test_should_not_claim_foreign_names(self):
        self.assertIsNone(self.importer.find_spec("unittest"))
        self.assertIsNone(self.importer.find_spec("unittest.mock"))
