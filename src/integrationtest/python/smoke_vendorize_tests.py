import unittest

from smoke_itest_support import SmokeIntegrationTestSupport


class SphinxSmokeTest(SmokeIntegrationTestSupport):
    PROJECT_FILES = list(SmokeIntegrationTestSupport.PROJECT_FILES) + ["docs"]

    def test_smoke_analyze_publish_no_integration_no_coverage(self):
        self.smoke_test("-v", "-X", "vendorize")


if __name__ == "__main__":
    unittest.main()
