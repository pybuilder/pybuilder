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


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin("copy_resources")
use_plugin("filter_resources")

@init
def init (project):
    project.get_property("copy_resources_glob").append("*")
    project.get_property("filter_resources_glob").append("spam")
        """)

        self.write_file("spam", "${version} ${any_undefined_key}")

        reactor = self.prepare_reactor()
        reactor.build("package")

        self.assert_file_content("target/spam", "1.0.dev0 ${any_undefined_key}")

if __name__ == "__main__":
    unittest.main()
