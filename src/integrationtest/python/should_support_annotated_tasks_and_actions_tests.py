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

import sys
import unittest

from integrationtest_support import IntegrationTestSupport


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
from pybuilder.core import task, before, Project, Logger

name = "test-project"

default_task = ["annotated_task"]


@task
def annotated_task(project: Project, logger: Logger):
    assert project is not None
    assert logger is not None

@before
def annotated_action(project: Project, logger: Logger):
    assert project is not None
    assert logger is not None

""")
        reactor = self.prepare_reactor()
        reactor.build(["annotated_task"])


if __name__ == "__main__":
    if sys.version_info[0] > 2:
        unittest.main()
