#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2015 PyBuilder Team
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

from integrationtest_support import IntegrationTestSupport
from pybuilder.errors import RequiredTaskExclusionException


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
from pybuilder.core import task, depends

@task
def task_a(project):
    project.set_property("a", False)

@task
@depends("task_a")
def task_b(project):
    project.set_property("a", True)

@task
@depends("task_a", "task_b")
def task_c(project):
    project.set_property("c", True)
        """)
        reactor = self.prepare_reactor()
        reactor.execution_manager.resolve_dependencies(exclude_optional_tasks=["task_b"])
        self.assertRaises(RequiredTaskExclusionException, reactor.execution_manager.build_execution_plan, "task_c")


if __name__ == "__main__":
    unittest.main()
