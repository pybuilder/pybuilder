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


import unittest

from itest_support import IntegrationTestSupport


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin("python.unittest")

default_task = ["verify"]

@init
def init (project):
    project.set_property("remote_debug", 2)
""")
        self.create_directory("src/main/python")
        self.create_directory("src/unittest/python")
        self.write_file("src/unittest/python/issue_770_tests.py", r"""
print("Hello")
   print("World!")
""")
        reactor = self.prepare_reactor()
        with self.assertRaises(IndentationError) as e:
            reactor.build()

        self.assertEqual(e.exception.lineno, 3)

        # This doesn't work on PyPy 3.7
        # self.assertEqual(e.exception.offset, 3)

        self.assertEqual(e.exception.text, '   print("World!")\n')


if __name__ == "__main__":
    unittest.main()
