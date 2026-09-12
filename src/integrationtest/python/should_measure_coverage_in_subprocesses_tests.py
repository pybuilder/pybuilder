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

from coverage_itest_support import SubprocessCoverageTestSupport, UNIT_TEST_REPORT
from itest_support import IntegrationTestSupport


class SubprocessCoverageTest(SubprocessCoverageTestSupport, IntegrationTestSupport):
    """A module that only ever runs in a subprocess still has to be measured.

    The VEnvs PyBuilder builds into have no Coverage installed and no startup hook
    of their own, so without the bootstrap the subprocess runs unmeasured and the
    module reports as entirely uncovered.
    """

    def test(self):
        self.write_measured_project("subprocess_coverage_tests",
                                    ["python.core", "python.unittest", "python.coverage"])

        reactor = self.prepare_reactor()
        reactor.build("coverage")

        self.assert_fully_covered(UNIT_TEST_REPORT, "covered_code.in_subprocess")


if __name__ == "__main__":
    unittest.main()
