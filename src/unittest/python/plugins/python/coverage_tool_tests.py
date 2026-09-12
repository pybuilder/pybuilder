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
from os.path import join as jp

from pybuilder.plugins.python.remote_tools.coverage_tool import CoverageTool
from test_utils import patch, Mock

SOURCE_PATH = jp("some", "project", "src", "main", "python", "")
OMIT_PATTERNS = [jp(SOURCE_PATH, "excluded_package", "*"), jp(SOURCE_PATH, "excluded_module.py")]

COV_ARGS = ("first-positional", "second-positional")
COV_KWARGS = {"branch": True, "data_suffix": True}


class CoverageToolTests(unittest.TestCase):
    """Exercises how the in-process tool that measures unit tests deals with a Coverage
    that is already running.

    With `--no-venvs` the unit tests run in the very Python that has Coverage installed,
    so Coverage's own startup hook measures the remoted process from before this tool
    gets a chance to. Stacking a second Coverage on top of that one would lose the first
    one's data and leave it to save itself without normalization.
    """

    def setUp(self):
        self.tool = CoverageTool(SOURCE_PATH, OMIT_PATTERNS, *COV_ARGS, **COV_KWARGS)
        self.pipe = Mock(name="pipe")

        for attribute, target in (("patch_coverage", "pybuilder.plugins.python._coverage_util.patch_coverage"),
                                  ("adopt", "pybuilder.plugins.python._coverage_util.adopt_subprocess_coverage"),
                                  ("save", "pybuilder.plugins.python._coverage_util.save_normalized_coverage"),
                                  ("coverage_factory", "coverage.coverage"),
                                  ):
            patcher = patch(target)
            setattr(self, attribute, patcher.start())
            self.addCleanup(patcher.stop)

    def test_should_normalize_the_paths_coverage_reports(self):
        self.tool.start(self.pipe)

        self.patch_coverage.assert_called_once_with()

    def test_should_start_its_own_coverage_when_no_startup_hook_did(self):
        self.adopt.return_value = None

        self.tool.start(self.pipe)

        self.adopt.assert_called_once_with(SOURCE_PATH, OMIT_PATTERNS)
        self.coverage_factory.assert_called_once_with(*COV_ARGS, **COV_KWARGS)
        self.assertIs(self.tool.coverage, self.coverage_factory.return_value)
        self.coverage_factory.return_value.start.assert_called_once_with()

    def test_should_adopt_what_a_startup_hook_started_instead_of_stacking_on_it(self):
        self.adopt.return_value = Mock(name="already_started")

        self.tool.start(self.pipe)

        self.adopt.assert_called_once_with(SOURCE_PATH, OMIT_PATTERNS)
        self.assertFalse(self.coverage_factory.called)
        self.assertIsNone(self.tool.coverage)

    def test_should_save_normalized_coverage_of_what_it_started(self):
        self.adopt.return_value = None
        self.tool.start(self.pipe)

        self.tool.stop(self.pipe)

        coverage = self.coverage_factory.return_value
        coverage.stop.assert_called_once_with()
        self.save.assert_called_once_with(coverage, SOURCE_PATH, OMIT_PATTERNS)

    def test_should_leave_the_save_to_whoever_adopted_what_was_already_running(self):
        self.adopt.return_value = Mock(name="already_started")
        self.tool.start(self.pipe)

        self.tool.stop(self.pipe)

        self.assertFalse(self.save.called)
        self.assertFalse(self.adopt.return_value.stop.called)

    def test_should_do_nothing_on_stop_when_it_was_never_started(self):
        self.tool.stop(self.pipe)

        self.assertFalse(self.save.called)


if __name__ == "__main__":
    unittest.main()
