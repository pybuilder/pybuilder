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

import sys
from functools import partial
from traceback import extract_stack
from unittest import TestCase

if sys.version_info[0] == 2:
    import mock
else:
    from unittest import mock


def _new_mock(*args, **kwargs):
    mock_type = kwargs["mock_type"]
    del kwargs["mock_type"]
    mock_kwargs = dict(kwargs)

    if "mock_name" in mock_kwargs:
        mock_name = mock_kwargs["mock_name"]
        del mock_kwargs["mock_name"]
        mock_kwargs["name"] = mock_name

    mock = mock_type(*args, **mock_kwargs)
    if "name" in kwargs:
        mock.name = kwargs["name"]
    return mock


class PyBuilderMock(mock.Mock):
    def __init__(self, spec=None, wraps=None, name=None, spec_set=None,
                 parent=None, _spec_state=None, _new_name='', _new_parent=None,
                 _spec_as_instance=False, _eat_self=None, unsafe=False, **kwargs):
        __dict__ = self.__dict__
        __dict__['_mock_tb'] = extract_stack()
        super(mock.Mock, self).__init__(spec=spec, wraps=wraps, name=name, spec_set=spec_set,
                                        parent=parent,
                                        _spec_state=_spec_state,
                                        _new_name=_new_name,
                                        _new_parent=_new_parent,
                                        _spec_as_instance=_spec_as_instance,
                                        _eat_self=_eat_self,
                                        unsafe=unsafe, **kwargs)


class PyBuilderMagicMock(mock.MagicMock):
    def __init__(self, spec=None, wraps=None, name=None, spec_set=None,
                 parent=None, _spec_state=None, _new_name='', _new_parent=None,
                 _spec_as_instance=False, _eat_self=None, unsafe=False, **kwargs):
        __dict__ = self.__dict__
        __dict__['_mock_tb'] = extract_stack()
        super(mock.MagicMock, self).__init__(spec=spec, wraps=wraps, name=name, spec_set=spec_set,
                                             parent=parent,
                                             _spec_state=_spec_state,
                                             _new_name=_new_name,
                                             _new_parent=_new_parent,
                                             _spec_as_instance=_spec_as_instance,
                                             _eat_self=_eat_self,
                                             unsafe=unsafe, **kwargs)


Mock = partial(_new_mock, mock_type=PyBuilderMock)
MagicMock = partial(_new_mock, mock_type=PyBuilderMagicMock)
patch = partial(mock.patch, new_callable=PyBuilderMagicMock)
patch.object = partial(mock.patch.object, new_callable=PyBuilderMagicMock)
patch.dict = mock.patch.dict
patch.multiple = partial(mock.patch.multiple, new_callable=PyBuilderMagicMock)
patch.stopall = mock.patch.stopall
mock_open = mock.mock_open
patch.TEST_PREFIX = 'test'
DEFAULT = mock.DEFAULT
call = mock.call
ANY = mock.ANY


class PyBuilderTestCase(TestCase):
    def assert_line_by_line_equal(self, expected_multi_line_string, actual_multi_line_string):
        expected_lines = expected_multi_line_string.split("\n")
        actual_lines = actual_multi_line_string.split("\n")
        for i in range(len(expected_lines)):
            expected_line = expected_lines[i]
            actual_line = actual_lines[i]
            message = """Multi-line strings are not equal in line ${line_number}
  expected: "{expected_line}"
   but got: "{actual_line}"
""".format(line_number=i, expected_line=expected_line, actual_line=actual_line)

            self.assertEquals(expected_line, actual_line, message)
        self.assertEquals(len(expected_lines), len(actual_lines),
                          'Multi-line strings do not have the same number of lines')


__all__ = [PyBuilderTestCase, Mock, MagicMock, patch, ANY, DEFAULT, call]
