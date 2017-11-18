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

from os import sep as os_sep
import unittest

from integrationtest_support import IntegrationTestSupport
from pybuilder.errors import BuildFailedException


failure_pytest_test_content = """
def test_pytest_base_failure():
    assert False
"""


class TestDefaultParamFailure(IntegrationTestSupport):
    def test_pytest(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin("python.pytest")

@init
def init (project):
    pass
        """)

        unittest_path = "src/unittest/python"
        unittest_file = unittest_path + os_sep + "failure_test.py"
        report_file = "target/reports/junit.xml"

        self.create_directory(unittest_path)
        self.write_file(unittest_file, failure_pytest_test_content)

        reactor = self.prepare_reactor()
        self.assertRaises(BuildFailedException, reactor.build, "run_unit_tests")

        self.assert_file_exists(unittest_file)
        self.assert_file_exists(report_file)

        self.assert_file_contains(report_file, 'tests="1"')
        self.assert_file_contains(report_file, 'errors="0"')
        self.assert_file_contains(report_file, 'failures="1"')
        self.assert_file_contains(report_file, 'skips="0"')


if __name__ == "__main__":
    unittest.main()
