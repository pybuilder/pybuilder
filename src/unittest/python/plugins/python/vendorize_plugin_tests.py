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

import ast
from unittest import TestCase

from pybuilder.plugins.python.vendorize_plugin import ImportTransformer

__author__ = "Arcadiy Ivanov"


class ImportTransformerTests(TestCase):
    def test_absolute_imports(self):
        self.assertEqual(self.get_transformed_source("""import b
        """, "/vendor/a.py", "/vendor", ["a", "b"]), """from . import b
        """)
        self.assertEqual(self.get_transformed_source("""import b
        """, "/vendor/a/__init__.py", "/vendor", ["a", "b"]), """from .. import b
        """)
        self.assertEqual(self.get_transformed_source("""import b
        """, "/vendor/a/x.py", "/vendor", ["a", "b"]), """from .. import b
        """)
        self.assertEqual(self.get_transformed_source("""import b
        """, "/vendor/a/x/__init__.py", "/vendor", ["a", "b"]), """from ... import b
        """)

    def test_relative_imports(self):
        self.assertEqual(self.get_transformed_source("""from b import x
        """, "/vendor/a.py", "/vendor", ["a", "b"]), """from .b import x
        """)
        self.assertEqual(self.get_transformed_source("""from b import x
        """, "/vendor/a/__init__.py", "/vendor", ["a", "b"]), """from ..b import x
        """)
        self.assertEqual(self.get_transformed_source("""from b import x
        """, "/vendor/a/x.py", "/vendor", ["a", "b"]), """from ..b import x
        """)
        self.assertEqual(self.get_transformed_source("""from b import x
        """, "/vendor/a/x/__init__.py", "/vendor", ["a", "b"]), """from ...b import x
        """)

    def get_transformed_source(self, source, source_path, vendorized_path, vendorized_packages):
        parsed_ast = ast.parse(source, filename=source_path)
        it = ImportTransformer(source_path, source, vendorized_path, vendorized_packages, [])
        it.visit(parsed_ast)
        return it.transformed_source
