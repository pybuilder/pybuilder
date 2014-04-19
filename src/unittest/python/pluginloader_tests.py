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
import unittest
import sys

builtin_module = None
try:
    import __builtin__
    builtin_module = __builtin__
except (ImportError) as e:
    import builtins
    builtin_module = builtins

from mockito import when, verify, unstub, never  # TODO @mriehl get rid of mockito here
from mock import patch, Mock, ANY
from test_utils import mock  # TODO @mriehl WTF is this sorcery?!

from pybuilder.errors import MissingPluginException
from pybuilder.pluginloader import (BuiltinPluginLoader,
                                    DispatchingPluginLoader,
                                    ThirdPartyPluginLoader,
                                    DownloadingPluginLoader,
                                    _install_external_plugin)


class ThirdPartyPluginLoaderTest(unittest.TestCase):

    def setUp(self):
        self.project = mock()
        self.loader = ThirdPartyPluginLoader(mock())

    def tearDown(self):
        unstub()

    def test_should_raise_exception_when_requiring_plugin_and_plugin_is_not_found(self):
        when(builtin_module).__import__(
            "spam").thenRaise(ImportError())

        self.assertRaises(
            MissingPluginException, self.loader.load_plugin, self.project, "spam")

        verify(builtin_module).__import__("spam")

    def test_should_import_plugin_when_requiring_plugin_and_plugin_is_found_as_third_party(self):
        old_module = sys.modules.get("spam")
        try:
            plugin_module = mock()
            sys.modules["spam"] = plugin_module
            when(builtin_module).__import__(
                "spam").thenReturn(plugin_module)

            self.loader.load_plugin(self.project, "spam")

            verify(builtin_module).__import__("spam")
        finally:
            del sys.modules["spam"]
            if old_module:
                sys.modules["spam"] = old_module

    def test_should_remove_pypi_protocol_when_importing(self):
        old_module = sys.modules.get("spam")
        try:
            plugin_module = mock()
            sys.modules["spam"] = plugin_module
            when(builtin_module).__import__(
                "pypi:spam").thenReturn(plugin_module)

            self.loader.load_plugin(self.project, "spam")

            verify(builtin_module).__import__("spam")
        finally:
            del sys.modules["spam"]
            if old_module:
                sys.modules["spam"] = old_module


class DownloadingPluginLoaderTest(unittest.TestCase):

    @patch("pybuilder.pluginloader.ThirdPartyPluginLoader")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_download_module_from_pypi(self, install, _):
        logger = Mock()
        DownloadingPluginLoader(logger).load_plugin(Mock(), "pypi:external_plugin")

        install.assert_called_with("pypi:external_plugin", logger)

    @patch("pybuilder.pluginloader.ThirdPartyPluginLoader.load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_load_module_after_downloading_when_download_succeeds(self, _, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        plugin = downloader.load_plugin(project, "pypi:external_plugin")

        load.assert_called_with(downloader, project, "pypi:external_plugin")
        self.assertEquals(plugin, load.return_value)

    @patch("pybuilder.pluginloader.ThirdPartyPluginLoader.load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_not_load_module_after_downloading_when_download_fails(self, install, load):
        install.side_effect = MissingPluginException("BOOM")
        downloader = DownloadingPluginLoader(Mock())
        plugin = downloader.load_plugin(Mock(), "pypi:external_plugin")

        self.assertFalse(load.called)
        self.assertEquals(plugin, None)


class InstallExternalPluginTests(unittest.TestCase):

    def test_should_raise_error_when_protocol_is_invalid(self):
        self.assertRaises(MissingPluginException, _install_external_plugin, "some-plugin", Mock())

    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pluginloader.execute_command")
    def test_should_install_plugin(self, execute, _):
        execute.return_value = 0

        _install_external_plugin("pypi:some-plugin", Mock())

        execute.assert_called_with('pip install some-plugin', ANY, shell=True, error_file_name=ANY)

    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pluginloader.execute_command")
    def test_should_raise_error_when_install_from_pypi_fails(self, execute, _):
        execute.return_value = 1

        self.assertRaises(MissingPluginException, _install_external_plugin, "pypi:some-plugin", Mock())


class BuiltinPluginLoaderTest(unittest.TestCase):

    def setUp(self):
        self.project = mock()
        self.loader = BuiltinPluginLoader(mock())

    def tearDown(self):
        unstub()

    def test_should_raise_exception_when_requiring_plugin_and_plugin_is_not_found(self):
        when(builtin_module).__import__(
            "pybuilder.plugins.spam_plugin").thenRaise(ImportError())

        self.assertRaises(
            MissingPluginException, self.loader.load_plugin, self.project, "spam")

        verify(builtin_module).__import__("pybuilder.plugins.spam_plugin")

    def test_should_import_plugin_when_requiring_plugin_and_plugin_is_found_as_builtin(self):
        old_module = sys.modules.get("pybuilder.plugins.spam_plugin")
        try:
            plugin_module = mock()
            sys.modules["pybuilder.plugins.spam_plugin"] = plugin_module
            when(builtin_module).__import__(
                "pybuilder.plugins.spam_plugin").thenReturn(plugin_module)

            self.loader.load_plugin(self.project, "spam")

            verify(builtin_module).__import__("pybuilder.plugins.spam_plugin")
        finally:
            del sys.modules["pybuilder.plugins.spam_plugin"]
            if old_module:
                sys.modules["pybuilder.plugins.spam_plugin"] = old_module


class DispatchingPluginLoaderTest (unittest.TestCase):

    def setUp(self):
        self.project = mock()
        self.fist_delegatee = mock()
        self.second_delegatee = mock()

        self.loader = DispatchingPluginLoader(
            mock, self.fist_delegatee, self.second_delegatee)

    def test_should_raise_exception_when_all_delgatees_raise_exception(self):
        when(self.fist_delegatee).load_plugin(
            self.project, "spam").thenRaise(MissingPluginException("spam"))
        when(self.second_delegatee).load_plugin(
            self.project, "spam").thenRaise(MissingPluginException("spam"))

        self.assertRaises(
            MissingPluginException, self.loader.load_plugin, self.project, "spam")

        verify(self.fist_delegatee).load_plugin(self.project, "spam")
        verify(self.second_delegatee).load_plugin(self.project, "spam")

    def test_should_return_module_returned_by_second_loader_when_first_delgatee_raises_exception(self):
        result = "result"
        when(self.fist_delegatee).load_plugin(
            self.project, "spam").thenRaise(MissingPluginException("spam"))
        when(self.second_delegatee).load_plugin(
            self.project, "spam").thenReturn(result)

        self.assertEquals(
            result, self.loader.load_plugin(self.project, "spam"))

        verify(self.fist_delegatee).load_plugin(self.project, "spam")
        verify(self.second_delegatee).load_plugin(self.project, "spam")

    def test_ensure_second_delegatee_is_not_trie_when_first_delegatee_loads_plugin(self):
        result = "result"
        when(self.fist_delegatee).load_plugin(
            self.project, "spam").thenReturn(result)

        self.assertEquals(
            result, self.loader.load_plugin(self.project, "spam"))

        verify(self.fist_delegatee).load_plugin(self.project, "spam")
        verify(self.second_delegatee, never).load_plugin(self.project, "spam")
