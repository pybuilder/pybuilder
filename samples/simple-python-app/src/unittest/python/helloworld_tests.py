#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from mockito import mock, when, any, unstub, verify
import unittest
import sys

from helloworld import helloworld

class HelloWorldTest (unittest.TestCase):
    def test_should_issue_hello_world_message (self):
        out = mock()

        helloworld(out)

        verify(out).write("Hello world of Python\n")
