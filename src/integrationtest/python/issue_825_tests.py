#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2021 PyBuilder Team
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


class Issue818Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file(
            """
from pybuilder.core import use_plugin, init

use_plugin("python.core")


@init
def initialize(project):
    project.set_property("verbose", True)
    assert project.environments == ("env", ) or project.environments == ()


@init(environments="env")
def initialize_env(project):
    assert project.environments == ("env", )
"""
        )

        reactor = self.prepare_reactor()
        reactor.build("prepare", environments=["env"])
        reactor.build("prepare")


if __name__ == "__main__":
    unittest.main()
