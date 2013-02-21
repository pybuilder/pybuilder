#  This file is part of Python Builder
#
#  Copyright 2011-2013 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest

from integrationtest_support import IntegrationTestSupport

class Test (IntegrationTestSupport):
    def test (self):
        self.write_build_file("""
from pybuilder.core import use_plugin

use_plugin("python.core")

name = "integration-test"
default_task = "publish"
""")
        self.create_directory("src/main/python/spam")
        self.write_file("src/main/python/spam/__init__.py", "")
        self.write_file("src/main/python/spam/eggs.py", """
def spam ():
    pass
""")

        reactor = self.prepare_reactor()
        reactor.build()

        self.assert_directory_exists("target/dist/integration-test-1.0-SNAPSHOT")
        self.assert_directory_exists("target/dist/integration-test-1.0-SNAPSHOT/spam")
        self.assert_file_empty("target/dist/integration-test-1.0-SNAPSHOT/spam/__init__.py")
        self.assert_file_content("target/dist/integration-test-1.0-SNAPSHOT/spam/eggs.py", """
def spam ():
    pass
""")

if __name__ == "__main__":
    unittest.main()
