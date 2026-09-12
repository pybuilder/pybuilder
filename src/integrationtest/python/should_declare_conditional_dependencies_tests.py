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


class ConditionalDependenciesTest(ConditionalDependenciesTestSupport):
    def test(self):
        reactor = self.build_project(extras="[]")

        setup_keywords = self.setup_call_keywords(reactor)

        # Both conditional pins are published, each carrying its own marker
        self.assertEqual(["six==1.15.0; python_version < '3.0'",
                          "six==1.17.0; python_version >= '3.0'"],
                         sorted(setup_keywords["install_requires"]))

        # Extras are published as extras and never as mandatory requirements
        self.assertEqual({"security": ["colorama>=0.4"],
                          "windows": ["pywin32>=300; sys_platform == 'win32'"]},
                         setup_keywords["extras_require"])

        # Only the applicable pin is constrained, so pip has nothing to intersect
        constraints = self.constraints(reactor)
        self.assertIn("six==1.17.0; python_version >= '3.0'", constraints)
        self.assertEqual(1, len([c for c in constraints if c.startswith("six")]), constraints)

        # Only the applicable pin is installed, and no extra is
        installed = self.installed(reactor)
        self.assertIn("six", installed)
        self.assertEqual("1.17.0", installed["six"].version)
        self.assertNotIn("colorama", installed)


if __name__ == "__main__":
    unittest.main()
