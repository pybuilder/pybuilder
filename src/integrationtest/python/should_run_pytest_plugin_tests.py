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

from os.path import join
import unittest

from integrationtest_support import IntegrationTestSupport


success_pytest_test_content = """
def test_pytest_base_success():
    assert True

def test_pytest_base_skip():
    assert True
"""


class TestCustomParamSuccess(IntegrationTestSupport):
    def test_pytest(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin("python.pytest")

@init
def init (project):
    project.set_property("dir_source_pytest_python", "some_dir/unittest")
    project.set_property("pytest_report_file", "some_dir/junit.xml")
    project.get_property("pytest_extra_args").append("-k")
    project.get_property("pytest_extra_args").append("test_pytest_base_success")
        """)

        unittest_path = "some_dir/unittest"
        unittest_file = join(unittest_path, "success_test.py")
        report_file = "some_dir/junit.xml"

        self.create_directory(unittest_path)
        self.write_file(unittest_file, success_pytest_test_content)

        reactor = self.prepare_reactor()
        reactor.build("run_unit_tests")

        self.assert_file_exists(unittest_file)
        self.assert_file_exists(report_file)

        self.assert_file_contains(report_file, 'tests="1"')
        self.assert_file_contains(report_file, 'errors="0"')
        self.assert_file_contains(report_file, 'failures="0"')
        self.assert_file_contains(report_file, 'skips="0"')


if __name__ == "__main__":
    unittest.main()
