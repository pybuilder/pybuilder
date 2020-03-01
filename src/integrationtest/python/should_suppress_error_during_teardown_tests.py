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

from integrationtest_support import IntegrationTestSupport

__author__ = 'arcivanov'


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
from pybuilder.core import task, before, after

@task
def foo():
    raise ValueError("simulated task failure")

@after(["foo"], teardown=True)
def teardown1_foo(project):
    raise ArithmeticError("simulated teardown error")

@after(["foo"], teardown=True)
def teardown2_foo(project):
    project.set_property("teardown2_foo completed", True)

        """)
        reactor = self.prepare_reactor()
        project = reactor.project

        self.assertRaises(ValueError, reactor.build, "foo")
        self.assertTrue(project.get_property("teardown2_foo completed"))


if __name__ == "__main__":
    unittest.main()
