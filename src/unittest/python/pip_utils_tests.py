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

from pybuilder import core
from pybuilder import pip_utils


class PipVersionTests(unittest.TestCase):
    def test_pip_dependency_version(self):
        self.assertEquals(pip_utils.build_dependency_version_string(core.Dependency("test", "1.2.3")), ">=1.2.3")
        self.assertEquals(pip_utils.build_dependency_version_string(core.Dependency("test", ">=1.2.3,<=2.3.4")),
                          "<=2.3.4,>=1.2.3")
        self.assertEquals(pip_utils.build_dependency_version_string("1.2.3"), ">=1.2.3")
        self.assertEquals(pip_utils.build_dependency_version_string(">=1.2.3,<=2.3.4"), "<=2.3.4,>=1.2.3")
        self.assertRaises(ValueError, pip_utils.build_dependency_version_string, "bogus")
