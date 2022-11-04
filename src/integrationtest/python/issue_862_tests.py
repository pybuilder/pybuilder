#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2022 PyBuilder Team
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


class Issue862Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file(
            textwrap.dedent(
                """
            from pybuilder.core import init, use_plugin

            use_plugin("python.core")
            use_plugin("python.unittest")
            use_plugin("python.coverage")

            name = "issue_862_tests"

            @init
            def init(project):
                project.set_property("coverage_break_build", False)
        """
            )
        )

        self.create_directory("src/main/python/code")
        self.create_directory("src/unittest/python")

        self.write_file(
            "src/main/python/code/__init__.py",
            textwrap.dedent(
                """
            from .two import return_two

            def return_one():
                return 1
            """
            ),
        )
        self.write_file(
            "src/main/python/code/two.py",
            textwrap.dedent(
                """
            def return_two():
                return 2
            """
            ),
        )
        self.write_file(
            "src/unittest/python/code_tests.py",
            textwrap.dedent(
                """
            import unittest
            import code

            class CodeTests(unittest.TestCase):
                def test_code(self):
                    self.assertEqual(code.return_one(), 1)

                def test_return_two(self):
                    self.assertEqual(code.return_two(), 2)
            """
            ),
        )

        reactor = self.prepare_reactor()
        reactor.build("coverage")

        coverage_file_path = "target/reports/issue_862_tests_coverage.xml"
        self.assert_file_not_contains(coverage_file_path, 'filename="/')
        self.assert_file_not_contains(coverage_file_path, '<package name=".')


if __name__ == "__main__":
    unittest.main()
