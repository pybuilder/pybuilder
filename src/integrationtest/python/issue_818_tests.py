#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2021 PyBuilder Team
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

import textwrap
import unittest

from itest_support import IntegrationTestSupport
from pybuilder.errors import BuildFailedException


class Issue818Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.pylint")

@init
def init (project):
    project.set_property("verbose", True)
    project.set_property("pylint_break_build", True)
        """)

        self.create_directory("src/main/python/a")
        self.create_directory("src/main/python/name/space")
        self.write_file("src/main/python/a/__init__.py", textwrap.dedent(
            """
            print("Hello from the package")
            """))
        self.write_file("src/main/python/a/module.py", textwrap.dedent(
            """
            print("Hello from the module")
            """))
        self.write_file("src/main/python/name/space/__init__.py", textwrap.dedent(
            """
            print("Hello from the namespace package")
            """))
        self.write_file("src/main/python/name/space/module.py", textwrap.dedent(
            """
            print("Hello from the namespace module")
            """))
        reactor = self.prepare_reactor()

        with self.assertRaises(BuildFailedException) as raised_e:
            reactor.build("analyze")

        self.assertEqual(raised_e.exception.message, "PyLint found 4 warning(s).")


if __name__ == "__main__":
    unittest.main()
