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

try:
    import __builtin__

    builtin_module = __builtin__
except ImportError as e:
    import builtins

    builtin_module = builtins

from test_utils import patch, Mock, ANY
from pybuilder.pip_utils import PIP_EXEC_STANZA
from pybuilder.errors import MissingPluginException, IncompatiblePluginException, UnspecifiedPluginNameException
from pybuilder.pluginloader import (BuiltinPluginLoader,
                                    DispatchingPluginLoader,
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
        plugin_module = Mock()
        pluginloader.PYB_VERSION = Version("1.2.3")
        plugin_module.pyb_version = "===1.2.3"
        _check_plugin_version(plugin_module, "test plugin")

    def test_version_compatible_match(self):
        plugin_module = Mock()
        pluginloader.PYB_VERSION = Version("1.2.3")
        plugin_module.pyb_version = "~=1.2"
        _check_plugin_version(plugin_module, "test plugin")

    def test_version_multiple_specifier_match(self):
        plugin_module = Mock()
        pluginloader.PYB_VERSION = Version("1.2.3")
        plugin_module.pyb_version = ">=1.2.0,<=1.2.4"
        _check_plugin_version(plugin_module, "test plugin")

    def test_version_no_match(self):
        plugin_module = Mock()
        pluginloader.PYB_VERSION = Version("1.2.3")
        plugin_module.pyb_version = ">=1.2.5"
        self.assertRaises(IncompatiblePluginException, _check_plugin_version, plugin_module, "test plugin")


class DownloadingPluginLoaderTest(unittest.TestCase):
    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_download_module_from_pypi(self, install, load):
        logger = Mock()
        project = Mock()
        project.get_property.side_effect = lambda x: "index_url" if x == "install_dependencies_index_url" \
            else "extra_index_url" if x == "install_dependencies_extra_index_url" else None
        load.side_effect = (MissingPluginException("external_plugin"), Mock())
        DownloadingPluginLoader(logger).load_plugin(project, "pypi:external_plugin")

        install.assert_called_with(project, "pypi:external_plugin", None, logger, None)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_load_module_after_downloading_with_pypi_when_download_succeeds(self, _, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        plugin = downloader.load_plugin(project, "pypi:external_plugin")

        load.assert_called_with("external_plugin", "pypi:external_plugin")
        self.assertEquals(plugin, load.return_value)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_not_load_module_twice_after_downloading_when_pypi_download_fails(self, install, load):
        install.side_effect = MissingPluginException("PyPI Install Boom")
        load.side_effect = MissingPluginException("PyPI Load Boom")
        downloader = DownloadingPluginLoader(Mock())
        self.assertRaises(MissingPluginException, downloader.load_plugin, Mock(), "pypi:external_plugin")

        self.assertEquals(load.call_count, 1)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_not_load_module_twice_after_downloading_when_vcs_download_fails(self, install, load):
        install.side_effect = MissingPluginException("VCS Install BOOM")
        load.side_effect = MissingPluginException("VCS Load Boom")
        downloader = DownloadingPluginLoader(Mock())
        self.assertRaises(MissingPluginException, downloader.load_plugin, Mock(), "vcs:external_plugin URL",
                          plugin_module_name="vcs_module_name")
        self.assertEquals(load.call_count, 1)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_fail_with_vcs_and_no_module_name(self, install, load):
        install.side_effect = MissingPluginException("VCS BOOM")
        downloader = DownloadingPluginLoader(Mock())
        self.assertRaises(UnspecifiedPluginNameException, downloader.load_plugin, Mock(), "vcs:external_plugin URL")

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

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_raise_exception_when_requiring_plugin_and_plugin_is_not_found(self, _, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        load.side_effect = MissingPluginException("Load boom")

        self.assertRaises(MissingPluginException, downloader.load_plugin, project, "spam")

        load.assert_called_with("spam", "spam")

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_import_plugin_when_requiring_plugin_and_plugin_is_found_as_third_party(self, install, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        load.return_value = Mock()

        self.assertEquals(load.return_value, downloader.load_plugin(project, "spam"))

        install.assert_not_called()
        self.assertEquals(install.call_count, 0)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_force_reinstall_vcs_plugin_before_first_loading_attempt(self, install, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        load.return_value = Mock()

        self.assertEquals(load.return_value, downloader.load_plugin(project, "vcs:spam", plugin_module_name="spam"))

        install.assert_called_with(project, "vcs:spam", None, downloader.logger, "spam", False, True)
        self.assertEquals(install.call_count, 1)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_update_pypi_plugin_with_non_exact_version_before_first_loading_attempt(self, install, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        load.return_value = Mock()

        self.assertEquals(load.return_value, downloader.load_plugin(project, "pypi:spam", ">1.2"))

        install.assert_called_with(project, "pypi:spam", ">1.2", downloader.logger, None, True, False)
        self.assertEquals(install.call_count, 1)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_update_pypi_plugin_with_compound_non_exact_version_before_first_loading_attempt(self, install,
                                                                                                    load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        load.return_value = Mock()

        self.assertEquals(load.return_value, downloader.load_plugin(project, "pypi:spam", ">1.2,==1.4"))

        install.assert_called_with(project, "pypi:spam", ">1.2,==1.4", downloader.logger, None, True, False)
        self.assertEquals(install.call_count, 1)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_not_update_pypi_plugin_with_exact_version_before_first_loading_attempt(self, install, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        plugin = Mock()
        load.side_effect = (MissingPluginException("no spam installed"), plugin)

        self.assertEquals(plugin, downloader.load_plugin(project, "pypi:spam", "===1.4"))

        install.assert_called_with(project, "pypi:spam", "===1.4", downloader.logger, None)
        self.assertEquals(install.call_count, 1)


class InstallExternalPluginTests(unittest.TestCase):
    def test_should_raise_error_when_protocol_is_invalid(self):
        self.assertRaises(MissingPluginException, _install_external_plugin, Mock(), "some-plugin", None, Mock(), None)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_install_plugin(self, execute, tempfile, read_file):
        read_file.return_value = ["no problems", "so far"]
        execute.return_value = 0
        tempfile.NamedTemporaryFile().__enter__().name.__eq__.return_value = True

        _install_external_plugin(Mock(), "pypi:some-plugin", None, Mock(), None)

        execute.assert_called_with(
            PIP_EXEC_STANZA + ['install', '--index-url', ANY, '--extra-index-url', ANY, '--trusted-host', ANY,
                               'some-plugin'], shell=False, outfile_name=ANY, error_file_name=ANY, cwd=".", env=ANY)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_install_plugin_with_version(self, execute, tempfile, read_file):
        read_file.return_value = ["no problems", "so far"]
        execute.return_value = 0
        tempfile.NamedTemporaryFile().__enter__().name.__eq__.return_value = True

        _install_external_plugin(Mock(), "pypi:some-plugin", "===1.2.3", Mock(), None)

        execute.assert_called_with(
            PIP_EXEC_STANZA + ['install', '--index-url', ANY, '--extra-index-url', ANY, '--trusted-host', ANY,
                               '--upgrade', 'some-plugin===1.2.3'], shell=False, outfile_name=ANY, error_file_name=ANY,
            cwd=".", env=ANY)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_install_plugin_with_vcs(self, execute, tempfile, read_file):
        read_file.return_value = ["no problems", "so far"]
        execute.return_value = 0
        tempfile.NamedTemporaryFile().__enter__().name.__eq__.return_value = True

        _install_external_plugin(Mock(), "vcs:some-plugin URL", None, Mock(), None)

        execute.assert_called_with(
            PIP_EXEC_STANZA + ['install', '--index-url', ANY, '--extra-index-url', ANY, '--trusted-host', ANY,
                               '--force-reinstall', 'some-plugin URL'], shell=False, outfile_name=ANY,
            error_file_name=ANY, cwd=".", env=ANY)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_install_plugin_with_vcs_and_version(self, execute, tempfile, read_file):
        read_file.return_value = ["no problems", "so far"]
        execute.return_value = 0
        tempfile.NamedTemporaryFile().__enter__().name.__eq__.return_value = True

        _install_external_plugin(Mock(), "vcs:some-plugin URL", "===1.2.3", Mock(), None)

        execute.assert_called_with(
            PIP_EXEC_STANZA + ['install', '--index-url', ANY, '--extra-index-url', ANY, '--trusted-host', ANY,
                               '--force-reinstall', 'some-plugin URL'], shell=False, outfile_name=ANY,
            error_file_name=ANY, cwd=".", env=ANY)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_raise_error_when_install_from_pypi_fails(self, execute, tempfile, read_file):
        read_file.return_value = ["something", "went wrong"]
        execute.return_value = 1
        tempfile.NamedTemporaryFile().__enter__().name.__eq__.return_value = True

        self.assertRaises(MissingPluginException, _install_external_plugin, Mock(), "pypi:some-plugin", None, Mock(), None)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pip_utils.execute_command")
    def test_should_raise_error_when_install_from_vcs_fails(self, execute, tempfile, read_file):
        read_file.return_value = ["something", "went wrong"]
        execute.return_value = 1
        tempfile.NamedTemporaryFile().__enter__().name.__eq__.return_value = True

        self.assertRaises(MissingPluginException, _install_external_plugin, Mock(), "vcs:some VCS URL", None, Mock(), None)


class BuiltinPluginLoaderTest(unittest.TestCase):
    def setUp(self):
        self.project = Mock()
        self.loader = BuiltinPluginLoader(Mock())

    @patch("pybuilder.pluginloader._load_plugin")
    def test_should_raise_exception_when_requiring_plugin_and_plugin_is_not_found(self, load):
        load.side_effect = MissingPluginException("pybuilder.plugins.spam_plugin")

        self.assertRaises(MissingPluginException, self.loader.load_plugin, self.project, "spam")

        load.assert_called_with("pybuilder.plugins.spam_plugin", "spam")

    @patch("pybuilder.pluginloader._load_plugin")
    def test_should_import_plugin_when_requiring_plugin_and_plugin_is_found_as_builtin(self, load):
        load.return_value = Mock()

        plugin_module = self.loader.load_plugin(self.project, "spam")

        load.assert_called_with("pybuilder.plugins.spam_plugin", "spam")
        self.assertEquals(load.return_value, plugin_module)


class DispatchingPluginLoaderTest(unittest.TestCase):
    def setUp(self):
        self.project = Mock()
        self.first_delegatee = Mock()
        self.second_delegatee = Mock()

        self.loader = DispatchingPluginLoader(
            Mock(), self.first_delegatee, self.second_delegatee)

    def test_should_raise_exception_when_all_delegatees_raise_exception(self):
        self.first_delegatee.load_plugin.side_effect = MissingPluginException("spam")
        self.second_delegatee.load_plugin.side_effect = MissingPluginException("spam")

        self.assertRaises(
            MissingPluginException, self.loader.load_plugin, self.project, "spam")

        self.first_delegatee.load_plugin.assert_called_with(self.project, "spam", None, None)
        self.second_delegatee.load_plugin.assert_called_with(self.project, "spam", None, None)

    def test_should_return_module_returned_by_second_loader_when_first_delegatee_raises_exception(self):
        result = "result"
        self.first_delegatee.load_plugin.side_effect = MissingPluginException("spam")
        self.second_delegatee.load_plugin.return_value = result

        self.assertEquals(result, self.loader.load_plugin(self.project, "spam"))

        self.first_delegatee.load_plugin.assert_called_with(self.project, "spam", None, None)
        self.second_delegatee.load_plugin.assert_called_with(self.project, "spam", None, None)

    def test_ensure_second_delegatee_will_not_try_when_first_delegatee_loads_plugin(self):
        result = "result"
        self.first_delegatee.load_plugin.return_value = result

        self.assertEquals(result, self.loader.load_plugin(self.project, "spam"))

        self.first_delegatee.load_plugin.assert_called_with(self.project, "spam", None, None)
        self.second_delegatee.load_plugin.assert_not_called()
