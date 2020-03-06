import unittest

from smoke_itest_support import SmokeIntegrationTestSupport


class CleanSmokeTest(SmokeIntegrationTestSupport):
    def test_clean(self):
        self.smoke_test("-v", "-X", "clean")

    def test_build_then_clean(self):
        self.smoke_test("-v", "-X", "compile_sources")
        self.smoke_test("-v", "-X", "clean")


if __name__ == "__main__":
    unittest.main()
