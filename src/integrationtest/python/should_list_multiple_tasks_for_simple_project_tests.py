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
        self.write_build_file("""
from pybuilder.core import task

@task
def another_task (): pass

@task("a_task_with_overridden_name")
def any_method_name (): pass

@task
def my_task (): pass
        """)
        reactor = self.prepare_reactor()

        actual_tasks = reactor.get_tasks()
        actual_task_names = [task.name for task in actual_tasks]

        self.assertEqual(
            ["a_task_with_overridden_name", "another_task", "my_task"], sorted(actual_task_names))


if __name__ == "__main__":
    unittest.main()
