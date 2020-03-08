import unittest

from smoke_itest_support import SmokeIntegrationTestSupport


class CleanSmokeTest(SmokeIntegrationTestSupport):
    def test_smoke_analyze_publish_no_integration_no_coverage(self):
        self.smoke_test("-v", "-X", "analyze", "publish",
                        "--force-exclude", "run_integration_tests",
                        "--force-exclude", "coverage")


if __name__ == "__main__":
    unittest.main()
