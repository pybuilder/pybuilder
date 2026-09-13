#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2026 PyBuilder Team
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

from conditional_deps_itest_support import ConditionalDependenciesTestSupport


class InstallSelectedExtrasIntoVenvsTest(ConditionalDependenciesTestSupport):
    def test(self):
        reactor = self.build_project(extras='["security"]')

        # The selected group is installed into both venvs, so the code it guards is testable
        for venv_name in ("build", "test"):
            installed = self.installed(reactor, venv_name)
            self.assertIn("colorama", installed, venv_name)
            self.assertIn("six", installed, venv_name)
            self.assertEqual("1.17.0", installed["six"].version, venv_name)

        # The unselected group is not installed
        self.assertNotIn("pywin32", self.installed(reactor))

        # Selecting a group for installation does not publish it as a mandatory requirement
        setup_keywords = self.setup_call_keywords(reactor)
        self.assertEqual(["six==1.15.0; python_version < '3.0'",
                          "six==1.17.0; python_version >= '3.0'"],
                         sorted(setup_keywords["install_requires"]))
        self.assertEqual(["colorama>=0.4"], setup_keywords["extras_require"]["security"])


if __name__ == "__main__":
    unittest.main()
