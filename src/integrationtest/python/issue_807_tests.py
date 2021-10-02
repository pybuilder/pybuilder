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

import sys
import textwrap
import unittest

from itest_support import IntegrationTestSupport


class Issue807Test(IntegrationTestSupport):
    def test(self):
        if sys.version_info[:2] < (3, 8):
            # importlib.metadata does not exist before Python 3.8
            return

        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")

@init
def init (project):
    project.set_property("verbose", True)
        """)

        self.create_directory("src/main/python")
        self.create_directory("src/unittest/python")
        self.write_file("src/main/python/code.py", textwrap.dedent(
            """
            from importlib import metadata

            def run_code():
                return metadata.version("setuptools")
            """))
        self.write_file("src/unittest/python/code_tests.py", textwrap.dedent(
            """
            import unittest
            import code

            class CodeTests(unittest.TestCase):
                def test_code(self):
                    code.run_code()
            """
        ))
        reactor = self.prepare_reactor()
        reactor.build("verify")


if __name__ == "__main__":
    unittest.main()
