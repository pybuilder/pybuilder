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

from pybuilder.core import Logger
from pybuilder.errors import BuildFailedException


class Issue867Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file(
            textwrap.dedent(
                """
            from pybuilder.core import init, use_plugin

            use_plugin("python.core")
            use_plugin("python.integrationtest")

            name = "issue_867_tests"

            @init
            def init(project):
                project.set_property("integrationtest_breaks_build", False)
        """
            )
        )

        self.create_directory("src/main/python/code")
        self.create_directory("src/integrationtest/python")

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
            "src/integrationtest/python/code_tests.py",
            textwrap.dedent(
                """
            import unittest
            import code

            class CodeTests(unittest.TestCase):
                def test_failure(self):
                    self.assertEqual(0, 1)

            if __name__ == "__main__":
                unittest.main()
            """
            ),
        )

        reactor = self.prepare_reactor(log_level=Logger.WARN)
        # This is the crux
        reactor.project.set_property("verbose", False)
        with self.assertRaises(BuildFailedException):
            reactor.build("run_integration_tests")


if __name__ == "__main__":
    unittest.main()
