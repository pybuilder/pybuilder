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

import sys
import unittest

from itest_support import IntegrationTestSupport

from pybuilder.errors import BuildFailedException


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file(
            """
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")

name = "unittest-integration-test"
default_task = "run_unit_tests"

@init
def init (project):
    project.build_depends_on("mockito")
"""
        )
        self.create_directory("src/main/python")
        self.write_file(
            "src/main/python/helloworld.py",
            r"""import sys

def helloworld(out):
    out.write("Hello world of Python\n")

""",
        )
        self.create_directory("src/unittest/python")
        self.write_file(
            "src/unittest/python/helloworld_tests.py",
            r"""from mockito import mock, verify
import unittest

from helloworld import helloworld

class HelloWorldTest(unittest.TestCase):
    def test_should_issue_hello_world_message(self):
        out = mock()

        helloworld(out)

        verify(out).write("Goodbye world of Python\n")
""",
        )

        reactor = self.prepare_reactor()
        try:
            reactor.build()
        except BuildFailedException:
            self.assertTrue("mockito" not in sys.modules)


if __name__ == "__main__":
    unittest.main()
