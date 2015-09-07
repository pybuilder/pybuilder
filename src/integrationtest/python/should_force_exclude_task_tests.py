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
        project = reactor.project
        reactor.execution_manager.resolve_dependencies(exclude_tasks=["task_b"])

        reactor.build("task_c")
        self.assertTrue(project.get_property("a") is not None)
        self.assertFalse(project.get_property("a"))
        self.assertTrue(project.get_property("c"))


if __name__ == "__main__":
    unittest.main()
