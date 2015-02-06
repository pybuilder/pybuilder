#  This file is part of PyBuilder
#
#  Copyright 2011-2015 The PyBuilder Team
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
from os.path import join

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        requirements = join(self.tmp_directory, "requirements.txt")
        self.write_build_file("""
from pybuilder.core import use_plugin

use_plugin("python.core")
use_plugin("python.distutils")

name = "integration-test"
default_task = "publish"

""".format(requirements))
        self.create_directory("src/main/python/spam")
        self.write_file("src/main/python/spam/__init__.py", "")

        self.create_directory("src/main/scripts")
        self.write_file("src/main/scripts/spam", "print('spam')")

        reactor = self.prepare_reactor()
        reactor.build()


if __name__ == "__main__":
    unittest.main()
