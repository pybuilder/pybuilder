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

from itest_support import IntegrationTestSupport


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file(
            """
from pybuilder.core import init, task

name = "integration-test"
default_task = "any_task"

@init(environments="test_environment")
def initialize ():
    raise Exception("Invoked although environment not defined")

@task
def any_task (): pass

"""
        )

        reactor = self.prepare_reactor()
        reactor.build()


if __name__ == "__main__":
    unittest.main()
