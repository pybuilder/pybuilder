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
import unittest

try:
    import __builtin__

    builtin_module = __builtin__
except ImportError as e:
    import builtins

    builtin_module = builtins

from mockito import when, verify, unstub, never  # TODO @mriehl get rid of mockito here
from mock import patch, Mock, ANY
from test_utils import mock  # TODO @mriehl WTF is this sorcery?!
from pybuilder.pip_utils import PIP_EXEC_STANZA
from pybuilder.errors import MissingPluginException, IncompatiblePluginException, UnspecifiedPluginNameException
from pybuilder.pluginloader import (BuiltinPluginLoader,
                                    DispatchingPluginLoader,
                                    ThirdPartyPluginLoader,
                                    DownloadingPluginLoader,
                                    _install_external_plugin,
                                    _check_plugin_version)
from pybuilder import pluginloader
from pip._vendor.packaging.version import Version


class PluginVersionCheckTest(unittest.TestCase):
    def setUp(self):
        self.old_pyb_version = pluginloader.PYB_VERSION

    def tearDown(self):
        pluginloader.PYB_VERSION = self.old_pyb_version

    def test_version_exact_match(self):
        plugin_module = mock()
        pluginloader.PYB_VERSION = Version("1.2.3")
        plugin_module.pyb_version = "===1.2.3"
        _check_plugin_version(plugin_module, "test plugin")

    def test_version_compatible_match(self):
        plugin_module = mock()
        pluginloader.PYB_VERSION = Version("1.2.3")
        plugin_module.pyb_version = "~=1.2"
        _check_plugin_version(plugin_module, "test plugin")

    def test_version_multiple_specifier_match(self):
        plugin_module = mock()
        pluginloader.PYB_VERSION = Version("1.2.3")
        plugin_module.pyb_version = ">=1.2.0,<=1.2.4"
        _check_plugin_version(plugin_module, "test plugin")

    def test_version_no_match(self):
        plugin_module = mock()
        pluginloader.PYB_VERSION = Version("1.2.3")
        plugin_module.pyb_version = ">=1.2.5"
        self.assertRaises(IncompatiblePluginException, _check_plugin_version, plugin_module, "test plugin")


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
            plugin_module.pyb_version = None
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
            plugin_module.pyb_version = None
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
        project = Mock()
        project.get_property.side_effect = lambda x: "index_url" if x == "install_dependencies_index_url" \
            else "extra_index_url" if x == "install_dependencies_extra_index_url" else None
        DownloadingPluginLoader(logger).load_plugin(project, "pypi:external_plugin")

        install.assert_called_with("pypi:external_plugin", None, logger, None, "index_url", "extra_index_url")

    @patch("pybuilder.pluginloader.ThirdPartyPluginLoader.load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_load_module_after_downloading_with_pypi_when_download_succeeds(self, _, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        plugin = downloader.load_plugin(project, "pypi:external_plugin")

        load.assert_called_with(downloader, project, "pypi:external_plugin", None, None)
        self.assertEquals(plugin, load.return_value)

    @patch("pybuilder.pluginloader.ThirdPartyPluginLoader.load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_not_load_module_after_downloading_when_pypi_download_fails(self, install, load):
        install.side_effect = MissingPluginException("PyPI BOOM")
        downloader = DownloadingPluginLoader(Mock())
        plugin = downloader.load_plugin(Mock(), "pypi:external_plugin")

        self.assertFalse(load.called)
        self.assertEquals(plugin, None)

    @patch("pybuilder.pluginloader.ThirdPartyPluginLoader.load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_not_load_module_after_downloading_when_vcs_download_fails(self, install, load):
        install.side_effect = MissingPluginException("VCS BOOM")
        downloader = DownloadingPluginLoader(Mock())
        plugin = downloader.load_plugin(Mock(), "vcs:external_plugin URL")

        self.assertFalse(load.called)
        self.assertEquals(plugin, None)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_fail_with_vcs_when_no_plugin_module_specified(self, _, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())

        self.assertRaises(UnspecifiedPluginNameException, downloader.load_plugin, project, "vcs:external_plugin URL")

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_load_module_after_downloading_with_vcs_when_download_succeeds(self, _, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        plugin = downloader.load_plugin(project, "vcs:external_plugin URL", plugin_module_name="external_plugin_module")

        load.assert_called_with("external_plugin_module", "vcs:external_plugin URL")
        self.assertEquals(plugin, load.return_value)


class InstallExternalPluginTests(unittest.TestCase):
    def test_should_raise_error_when_protocol_is_invalid(self):
        self.assertRaises(MissingPluginException, _install_external_plugin, "some-plugin", None, Mock(), None)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_install_plugin(self, execute, _, read_file):
        read_file.return_value = ["no problems", "so far"]
        execute.return_value = 0

        _install_external_plugin("pypi:some-plugin", None, Mock(), None)

        execute.assert_called_with(PIP_EXEC_STANZA + ['install', 'some-plugin'], shell=False,
                                   outfile_name=ANY, error_file_name=ANY, cwd=".", env=ANY)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_install_plugin_with_version(self, execute, _, read_file):
        read_file.return_value = ["no problems", "so far"]
        execute.return_value = 0

        _install_external_plugin("pypi:some-plugin", "===1.2.3", Mock(), None)

        execute.assert_called_with(PIP_EXEC_STANZA + ['install', '--upgrade', 'some-plugin===1.2.3'], shell=False,
                                   outfile_name=ANY, error_file_name=ANY, cwd=".", env=ANY)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_install_plugin_with_vcs(self, execute, _, read_file):
        read_file.return_value = ["no problems", "so far"]
        execute.return_value = 0

        _install_external_plugin("vcs:some-plugin URL", None, Mock(), None)

        execute.assert_called_with(PIP_EXEC_STANZA + ['install', '--force-reinstall', 'some-plugin URL'], shell=False,
                                   outfile_name=ANY, error_file_name=ANY, cwd=".", env=ANY)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_install_plugin_with_vcs_and_version(self, execute, _, read_file):
        read_file.return_value = ["no problems", "so far"]
        execute.return_value = 0

        _install_external_plugin("vcs:some-plugin URL", "===1.2.3", Mock(), None)

        execute.assert_called_with(PIP_EXEC_STANZA + ['install', '--force-reinstall', 'some-plugin URL'], shell=False,
                                   outfile_name=ANY, error_file_name=ANY, cwd=".", env=ANY)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_raise_error_when_install_from_pypi_fails(self, execute, _, read_file):
        read_file.return_value = ["something", "went wrong"]
        execute.return_value = 1

        self.assertRaises(MissingPluginException, _install_external_plugin, "pypi:some-plugin", None, Mock(), None)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_raise_error_when_install_from_vcs_fails(self, execute, _, read_file):
        read_file.return_value = ["something", "went wrong"]
        execute.return_value = 1

        self.assertRaises(MissingPluginException, _install_external_plugin, "vcs:some VCS URL", None, Mock(), None)


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
            plugin_module.pyb_version = None
            sys.modules["pybuilder.plugins.spam_plugin"] = plugin_module
            when(builtin_module).__import__(
                "pybuilder.plugins.spam_plugin").thenReturn(plugin_module)

            self.loader.load_plugin(self.project, "spam")

            verify(builtin_module).__import__("pybuilder.plugins.spam_plugin")
        finally:
            del sys.modules["pybuilder.plugins.spam_plugin"]
            if old_module:
                sys.modules["pybuilder.plugins.spam_plugin"] = old_module


class DispatchingPluginLoaderTest(unittest.TestCase):
    def setUp(self):
        self.project = mock()
        self.first_delegatee = mock()
        self.second_delegatee = mock()

        self.loader = DispatchingPluginLoader(
            mock, self.first_delegatee, self.second_delegatee)

    def test_should_raise_exception_when_all_delegatees_raise_exception(self):
        when(self.first_delegatee).load_plugin(
            self.project, "spam", None, None).thenRaise(MissingPluginException("spam"))
        when(self.second_delegatee).load_plugin(
            self.project, "spam", None, None).thenRaise(MissingPluginException("spam"))

        self.assertRaises(
            MissingPluginException, self.loader.load_plugin, self.project, "spam")

        verify(self.first_delegatee).load_plugin(self.project, "spam", None, None)
        verify(self.second_delegatee).load_plugin(self.project, "spam", None, None)

    def test_should_return_module_returned_by_second_loader_when_first_delegatee_raises_exception(self):
        result = "result"
        when(self.first_delegatee).load_plugin(
            self.project, "spam", None, None).thenRaise(MissingPluginException("spam"))
        when(self.second_delegatee).load_plugin(
            self.project, "spam", None, None).thenReturn(result)

        self.assertEquals(
            result, self.loader.load_plugin(self.project, "spam"))

        verify(self.first_delegatee).load_plugin(self.project, "spam", None, None)
        verify(self.second_delegatee).load_plugin(self.project, "spam", None, None)

    def test_ensure_second_delegatee_will_not_try_when_first_delegatee_loads_plugin(self):
        result = "result"
        when(self.first_delegatee).load_plugin(
            self.project, "spam", None, None).thenReturn(result)

        self.assertEquals(
            result, self.loader.load_plugin(self.project, "spam"))

        verify(self.first_delegatee).load_plugin(self.project, "spam", None, None)
        verify(self.second_delegatee, never).load_plugin(self.project, "spam", None, None)
