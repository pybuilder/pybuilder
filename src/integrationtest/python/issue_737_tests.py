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
from pybuilder.core import use_plugin, init
import sys
from os.path import join as jp, normcase as nc, dirname

build_sources = nc(jp(dirname(__file__), "src/main/python"))
if build_sources not in sys.path:
    sys.path.insert(0, build_sources)

use_plugin("issue_737_plugin_2")
use_plugin("issue_737_plugin_1")

name = "pybuilder-defaults-plugin"
version = "1.1.1"
summary = "PyBuilder plugin to provide common configuration for python projects"
default_task = ["task2"]

@init
def init (project):
    pass
""")
        self.create_directory("src/main/python")
        self.write_file("src/main/python/issue_737_plugin_1.py", r"""
from pybuilder.core import init, task, depends

@task
def task1():
    pass

@task
@depends("task1")
def task2():
    pass
""")
        self.write_file("src/main/python/issue_737_plugin_2.py", r"""
from pybuilder.core import init, use_plugin, task, depends, dependents, optional

@task
@depends("task1")
@dependents(optional("task2"))
def taskX():
    pass
""")
        reactor = self.prepare_reactor()
        reactor.build()


if __name__ == "__main__":
    unittest.main()
