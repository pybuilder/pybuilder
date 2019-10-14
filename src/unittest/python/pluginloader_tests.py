#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2019 PyBuilder Team
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

from pybuilder import pip_common
from pybuilder import pluginloader
from pybuilder.core import PluginDef, Dependency
from pybuilder.errors import MissingPluginException, IncompatiblePluginException
from pybuilder.pluginloader import (BuiltinPluginLoader,
                                    DispatchingPluginLoader,
                                    DownloadingPluginLoader,
                                    _check_plugin_version)
from test_utils import patch, Mock


class PluginVersionCheckTest(unittest.TestCase):
    def setUp(self):
        self.old_pyb_version = pluginloader.PYB_VERSION

    def tearDown(self):
        pluginloader.PYB_VERSION = self.old_pyb_version

    def test_version_exact_match(self):
        plugin_module = Mock()
        pluginloader.PYB_VERSION = pip_common.Version("1.2.3")
        plugin_module.pyb_version = "===1.2.3"
        _check_plugin_version(plugin_module, "test plugin")

    def test_version_compatible_match(self):
        plugin_module = Mock()
        pluginloader.PYB_VERSION = pip_common.Version("1.2.3")
        plugin_module.pyb_version = "~=1.2"
        _check_plugin_version(plugin_module, "test plugin")

    def test_version_multiple_specifier_match(self):
        plugin_module = Mock()
        pluginloader.PYB_VERSION = pip_common.Version("1.2.3")
        plugin_module.pyb_version = ">=1.2.0,<=1.2.4"
        _check_plugin_version(plugin_module, "test plugin")

    def test_version_no_match(self):
        plugin_module = Mock()
        pluginloader.PYB_VERSION = pip_common.Version("1.2.3")
        plugin_module.pyb_version = ">=1.2.5"
        self.assertRaises(IncompatiblePluginException, _check_plugin_version, plugin_module, "test plugin")


class DownloadingPluginLoaderTest(unittest.TestCase):

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_download_module_from_pypi(self, install, load):
        logger = Mock()
        project = Mock()
        project.get_property.side_effect = lambda x: "index_url" if x == "install_dependencies_index_url" \
            else "extra_index_url" if x == "install_dependencies_extra_index_url" else None
        load.side_effect = (MissingPluginException("external_plugin"), Mock())

        pd = PluginDef("pypi:external_plugin")
        pl = DownloadingPluginLoader(logger)
        pl.install_plugin(project, pd)

        install.assert_called_with(logger, project,
                                   [Dependency("external_plugin")],
                                   project.plugin_dir, project.plugin_install_log,
                                   package_type="plugin")

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_load_module_after_downloading_with_pypi_when_download_succeeds(self, _, load):
        logger = Mock()
        project = Mock()
        downloader = DownloadingPluginLoader(logger)
        pd = PluginDef("pypi:external_plugin")
        plugin = downloader.load_plugin(project, pd)

        load.assert_called_with("external_plugin", pd.name)
        self.assertEqual(plugin, load.return_value)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_not_load_module_twice_after_downloading_when_pypi_download_fails(self, install, load):
        logger = Mock()
        install.side_effect = MissingPluginException("PyPI Install Boom")
        load.side_effect = MissingPluginException("PyPI Load Boom")
        downloader = DownloadingPluginLoader(logger)
        pd = PluginDef("pypi:external_plugin")
        self.assertRaises(MissingPluginException, downloader.load_plugin, Mock(), pd)

        self.assertEqual(load.call_count, 1)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_not_load_module_twice_after_downloading_when_vcs_download_fails(self, install, load):
        install.side_effect = MissingPluginException("VCS Install BOOM")
        load.side_effect = MissingPluginException("VCS Load Boom")
        downloader = DownloadingPluginLoader(Mock())
        pd = PluginDef("vcs:external_plugin URL", plugin_module_name="vcs_module_name")
        self.assertRaises(MissingPluginException, downloader.load_plugin, Mock(), pd)
        self.assertEqual(load.call_count, 1)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_load_module_after_downloading_with_vcs_when_download_succeeds(self, _, load):
        logger = Mock()
        project = Mock()
        downloader = DownloadingPluginLoader(logger)
        pd = PluginDef("vcs:external_plugin URL", plugin_module_name="external_plugin_module")
        plugin = downloader.load_plugin(project, pd)

        load.assert_called_with("external_plugin_module", "vcs:external_plugin URL")
        self.assertEqual(plugin, load.return_value)

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_raise_exception_when_requiring_plugin_and_plugin_is_not_found(self, _, load):
        logger = Mock()
        project = Mock()
        downloader = DownloadingPluginLoader(logger)
        load.side_effect = MissingPluginException("Load boom")

        self.assertRaises(MissingPluginException, downloader.load_plugin, project, PluginDef("spam"))

        load.assert_called_with("spam", "spam")

    @patch("pybuilder.pluginloader._load_plugin")
    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_import_plugin_when_requiring_plugin_and_plugin_is_found_as_third_party(self, install, load):
        logger = Mock()
        project = Mock()
        downloader = DownloadingPluginLoader(logger)
        load.return_value = Mock()

        self.assertEqual(load.return_value, downloader.load_plugin(project, PluginDef("spam")))

        install.assert_not_called()
        self.assertEqual(install.call_count, 0)

    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_raise_error_when_protocol_is_invalid(self, install):
        logger = Mock()
        project = Mock()
        downloader = DownloadingPluginLoader(logger)

        self.assertRaises(MissingPluginException, downloader.install_plugin, project, PluginDef("some-plugin"))

    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_install_plugin(self, install):
        logger = Mock()
        project = Mock()
        project.get_property.return_value = 0

        pd = PluginDef("pypi:some-plugin")
        downloader = DownloadingPluginLoader(logger)
        downloader.install_plugin(project, pd)

        install.assert_called_with(logger, project,
                                   [pd.dependency],
                                   project.plugin_dir, project.plugin_install_log,
                                   package_type="plugin")

    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_install_plugin_with_version(self, install):
        logger = Mock()
        project = Mock()
        project.get_property.return_value = 0

        pd = PluginDef("pypi:some-plugin", "===1.2.3")
        downloader = DownloadingPluginLoader(logger)
        downloader.install_plugin(project, pd)

        install.assert_called_with(logger, project,
                                   [pd.dependency],
                                   project.plugin_dir, project.plugin_install_log,
                                   package_type="plugin")

    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_install_upgrade_plugin_with_non_exact_version(self, install):
        logger = Mock()
        project = Mock()
        project.get_property.return_value = 0

        pd = PluginDef("pypi:some-plugin", "~=1.2.3")
        downloader = DownloadingPluginLoader(logger)
        downloader.install_plugin(project, pd)

        install.assert_called_with(logger, project,
                                   [pd.dependency],
                                   project.plugin_dir, project.plugin_install_log,
                                   package_type="plugin")

    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_install_plugin_with_vcs(self, install):
        logger = Mock()
        project = Mock()
        project.get_property.return_value = 0

        pd = PluginDef("vcs:some-plugin URL", plugin_module_name="module_name")
        downloader = DownloadingPluginLoader(logger)
        downloader.install_plugin(project, pd)

        install.assert_called_with(logger, project,
                                   [pd.dependency],
                                   project.plugin_dir, project.plugin_install_log,
                                   package_type="plugin")

    @patch("pybuilder.pluginloader.install_dependencies")
    def test_should_install_plugin_with_vcs_and_version(self, install):
        logger = Mock()
        project = Mock()
        project.get_property.return_value = 0

        pd = PluginDef("vcs:some-plugin URL", "===1.2.3", "module_name")
        downloader = DownloadingPluginLoader(logger)
        downloader.install_plugin(project, pd)

        install.assert_called_with(logger, project,
                                   [pd.dependency],
                                   project.plugin_dir, project.plugin_install_log,
                                   package_type="plugin")


class BuiltinPluginLoaderTest(unittest.TestCase):
    def setUp(self):
        self.project = Mock()
        self.loader = BuiltinPluginLoader(Mock())

    @patch("pybuilder.pluginloader._load_plugin")
    def test_should_raise_exception_when_requiring_plugin_and_plugin_is_not_found(self, load):
        load.side_effect = MissingPluginException("pybuilder.plugins.spam_plugin")

        self.assertRaises(MissingPluginException, self.loader.load_plugin, self.project, PluginDef("spam"))

        load.assert_called_with("pybuilder.plugins.spam_plugin", "spam")

    @patch("pybuilder.pluginloader._load_plugin")
    def test_should_import_plugin_when_requiring_plugin_and_plugin_is_found_as_builtin(self, load):
        load.return_value = Mock()

        plugin_module = self.loader.load_plugin(self.project, PluginDef("spam"))

        load.assert_called_with("pybuilder.plugins.spam_plugin", "spam")
        self.assertEqual(load.return_value, plugin_module)


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

        pd = PluginDef("spam")

        self.assertRaises(
            MissingPluginException, self.loader.load_plugin, self.project, pd)

        self.first_delegatee.load_plugin.assert_called_with(self.project, pd)
        self.second_delegatee.load_plugin.assert_called_with(self.project, pd)

    def test_should_return_module_returned_by_second_loader_when_first_delegatee_raises_exception(self):
        result = "result"
        self.first_delegatee.load_plugin.side_effect = MissingPluginException("spam")
        self.second_delegatee.load_plugin.return_value = result

        pd = PluginDef("spam")
        self.assertEqual(result, self.loader.load_plugin(self.project, pd))

        self.first_delegatee.load_plugin.assert_called_with(self.project, pd)
        self.second_delegatee.load_plugin.assert_called_with(self.project, pd)

    def test_ensure_second_delegatee_will_not_try_when_first_delegatee_loads_plugin(self):
        result = "result"
        self.first_delegatee.load_plugin.return_value = result

        pd = PluginDef("spam")
        self.assertEqual(result, self.loader.load_plugin(self.project, pd))

        self.first_delegatee.load_plugin.assert_called_with(self.project, pd)
        self.second_delegatee.load_plugin.assert_not_called()
