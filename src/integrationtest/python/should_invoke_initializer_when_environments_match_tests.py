#  This file is part of Python Builder
#   
#  Copyright 2011 The Python Builder Team
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
from pythonbuilder.core import init, task

name = "integration-test"
default_task = "any_task"

@init(environments="test_environment")
def initialize (project):
    setattr(project, "INITIALIZER_EXECUTED", True)

@task
def any_task (project):
    if not hasattr(project, "INITIALIZER_EXECUTED"):
        raise Exception("Initializer has not been executed")

""")

        reactor = self.prepare_reactor()
        reactor.build(environments=["test_environment"])

if __name__ == "__main__":
    unittest.main()
