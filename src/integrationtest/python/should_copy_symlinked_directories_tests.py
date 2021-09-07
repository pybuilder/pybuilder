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

import os
import unittest

from itest_support import IntegrationTestSupport


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin("python.core")

@init
def init (project):
    pass
        """)

        self.create_directory("src/main/python")
        self.create_directory("common/symlinked")
        self.write_file("common/symlinked/cargo")
        os.symlink("../../../common/symlinked", self.full_path("src/main/python/symlinked"), target_is_directory=True)

        reactor = self.prepare_reactor()
        reactor.build("package")
        project = reactor.project

        self.assert_file_exists(project.expand_path("$dir_dist/symlinked/cargo"))


if __name__ == "__main__":
    unittest.main()
