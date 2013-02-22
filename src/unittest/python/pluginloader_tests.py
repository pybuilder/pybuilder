#  This file is part of Python Builder
#
#  Copyright 2011-2013 PyBuilder Team
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
import unittest
import sys

builtin_module = None
try:
    import __builtin__
    builtin_module = __builtin__
except (ImportError) as e:
    import builtins
    builtin_module = builtins

from mockito import when, verify, unstub, never
from test_utils import mock

from pybuilder.errors import MissingPluginException
from pybuilder.pluginloader import BuiltinPluginLoader, DispatchingPluginLoader

class BuiltinPluginLoaderTest (unittest.TestCase):
    def setUp (self):
        super(BuiltinPluginLoaderTest, self).setUp()
        self.project = mock()
        self.loader = BuiltinPluginLoader(mock())

    def tearDown (self):
        super(BuiltinPluginLoaderTest, self).tearDown()
        unstub()

    def test_should_raise_exception_when_requiring_plugin_and_plugin_is_not_found (self):
        when(builtin_module).__import__("pybuilder.plugins.spam_plugin").thenRaise(ImportError())

        self.assertRaises(MissingPluginException, self.loader.load_plugin, self.project, "spam")

        verify(builtin_module).__import__("pybuilder.plugins.spam_plugin")

    def test_should_import_plugin_when_requiring_plugin_and_plugin_is_found_as_builtin (self):
        old_module = sys.modules.get("pybuilder.plugins.spam_plugin")
        try:
            plugin_module = mock()
            sys.modules["pybuilder.plugins.spam_plugin"] = plugin_module
            when(builtin_module).__import__("pybuilder.plugins.spam_plugin").thenReturn(plugin_module)

            self.loader.load_plugin(self.project, "spam")

            verify(builtin_module).__import__("pybuilder.plugins.spam_plugin")
        finally:
            del sys.modules["pybuilder.plugins.spam_plugin"]
            if old_module:
                sys.modules["pybuilder.plugins.spam_plugin"] = old_module


class DispatchingPluginLoaderTest (unittest.TestCase):
    def setUp (self):
        self.project = mock()
        self.fist_delegatee = mock()
        self.second_delegatee = mock()

        self.loader = DispatchingPluginLoader(mock, self.fist_delegatee, self.second_delegatee)

    def test_should_raise_exception_when_all_delgatees_raise_exception (self):
        when(self.fist_delegatee).load_plugin(self.project, "spam").thenRaise(MissingPluginException("spam"))
        when(self.second_delegatee).load_plugin(self.project, "spam").thenRaise(MissingPluginException("spam"))

        self.assertRaises(MissingPluginException, self.loader.load_plugin, self.project, "spam")

        verify(self.fist_delegatee).load_plugin(self.project, "spam")
        verify(self.second_delegatee).load_plugin(self.project, "spam")

    def test_should_return_module_returned_by_second_loader_when_first_delgatee_raises_exception (self):
        result = "result"
        when(self.fist_delegatee).load_plugin(self.project, "spam").thenRaise(MissingPluginException("spam"))
        when(self.second_delegatee).load_plugin(self.project, "spam").thenReturn(result)

        self.assertEquals(result, self.loader.load_plugin(self.project, "spam"))

        verify(self.fist_delegatee).load_plugin(self.project, "spam")
        verify(self.second_delegatee).load_plugin(self.project, "spam")

    def test_ensure_second_delegatee_is_not_trie_when_first_delegatee_loads_plugin (self):
        result = "result"
        when(self.fist_delegatee).load_plugin(self.project, "spam").thenReturn(result)

        self.assertEquals(result, self.loader.load_plugin(self.project, "spam"))

        verify(self.fist_delegatee).load_plugin(self.project, "spam")
        verify(self.second_delegatee, never).load_plugin(self.project, "spam")
