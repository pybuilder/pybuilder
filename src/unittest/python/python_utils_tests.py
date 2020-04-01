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
from shutil import rmtree
from tempfile import mkdtemp

from pybuilder.python_utils import iglob, makedirs
from pybuilder.utils import jp


class TestPythonGlobTest(unittest.TestCase):
    def touch(self, f):
        with open(f, "wb") as f:
            pass

    def setUp(self):
        self.tmp_dir = mkdtemp()

        makedirs(jp(self.tmp_dir, "a", "b"))
        self.touch(jp(self.tmp_dir, "x.py"))
        self.touch(jp(self.tmp_dir, "a", "y.py"))
        self.touch(jp(self.tmp_dir, "a", "b", "z.py"))

    def tearDown(self):
        rmtree(self.tmp_dir)

    def test_iglob(self):
        self.assertEqual(list(iglob(jp(self.tmp_dir, "*.py"))), [jp(self.tmp_dir, "x.py")])
        self.assertEqual(list(iglob(jp(self.tmp_dir, "**", "*.py"), recursive=True)),
                         [jp(self.tmp_dir, "x.py"),
                          jp(self.tmp_dir, "a", "y.py"),
                          jp(self.tmp_dir, "a", "b", "z.py")
                          ])
