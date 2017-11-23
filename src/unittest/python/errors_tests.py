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

from pybuilder.errors import PyBuilderException


class PyBuilderExceptionTest(unittest.TestCase):
    def test_should_format_exception_message_without_arguments(self):
        self.assertEqual("spam and eggs", str(PyBuilderException("spam and eggs")))

    def test_should_format_exception_message_with_arguments(self):
        self.assertEqual("spam and eggs", str(PyBuilderException("%s and %s", "spam", "eggs")))
