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

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin

use_plugin("python.pyfix_unittest")

name = "integration-test"
default_task = "run_unit_tests"
""")
        self.create_directory("src/unittest/python")
        self.write_file("src/unittest/python/spam_pyfix_tests.py", """
import time

from pyfix import test

@test
def should_run_pyfix_test ():
    time.sleep(.1)
""")
        self.write_file("src/unittest/python/cheese_tests.py", """
import time

from pyfix import test

@test
def should_skip_test_sans_pyfix_test ():
    raise Exception("This test should not have run!")
""")

        reactor = self.prepare_reactor()
        reactor.build()

        self.assert_file_contains(
            "target/reports/pyfix_unittest.json", '"failures": []')
        self.assert_file_contains(
            "target/reports/pyfix_unittest.json", '"tests-run": 1')

if __name__ == "__main__":
    unittest.main()
