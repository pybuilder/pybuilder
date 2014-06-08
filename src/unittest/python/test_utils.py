#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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

from unittest import TestCase
import mockito


def mock(mocked_obj=None, **keyword_arguments):
    result = mockito.mock(mocked_obj)
    for key in keyword_arguments:
        setattr(result, key, keyword_arguments[key])
    return result


class PyBuilderTestCase(TestCase):

    def assert_line_by_line_equal(self, expected_multi_line_string, actual_multi_line_string):
        expected_lines = expected_multi_line_string.split("\n")
        actual_lines = actual_multi_line_string.split("\n")
        for i in range(len(expected_lines)):
            expected_line = expected_lines[i]
            actual_line = actual_lines[i]
            message = """Multi line strings are not equal in line ${line_number}
  expected: "{expected_line}"
   but got: "{actual_line}"
""".format(line_number=i, expected_line=expected_line, actual_line=actual_line)

            self.assertEqual(expected_line, actual_line, message)
