#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2020 PyBuilder Team
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

from smoke_itest_support import SmokeIntegrationTestSupport


class VendorizeSmokeTest(SmokeIntegrationTestSupport):
    PROJECT_FILES = list(SmokeIntegrationTestSupport.PROJECT_FILES) + ["docs"]

    def test_smoke_analyze_publish_no_integration_no_coverage(self):
        self.smoke_test("-v", "-X", "vendorize")


if __name__ == "__main__":
    unittest.main()
