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


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
from pybuilder.core import init
from pybuilder.core import task
from pybuilder.core import use_plugin

use_plugin("python.pyfix_unittest")

name = "integration-test"
default_task = ["run_unit_tests", "test_override"]

@task
def test_override(project):
    file_suffix = project.get_property("pyfix_unittest_file_suffix")
    module_glob = project.get_property("pyfix_unittest_module_glob")
    if module_glob != "*{0}".format(file_suffix)[:-3]:
        raise Exception("pyfix_unittest_file_suffix failed to override pyfix_unittest_module_glob")

@init
def init_should_set_pyfix_glob_from_suffix(project):
    project.set_property("pyfix_unittest_module_glob", "suffix will overwrite")
    project.set_property("pyfix_unittest_file_suffix", "_pyfix_tests.py")
""")
        self.create_directory("src/unittest/python")
        self.write_file("src/unittest/python/spam_pyfix_tests.py", """
from pyfix import test

@test
def should_run_pyfix_test ():
    return
""")
        self.write_file("src/unittest/python/cheese_tests.py", """
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
