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

"""
    The PyBuilder pluginloader module.
    Provides a mechanism to load PyBuilder plugins.
"""

import sys
import tempfile

from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import Version

from pybuilder import __version__ as pyb_version
from pybuilder.errors import MissingPluginException, IncompatiblePluginException
from pybuilder.utils import execute_command, read_file

PYPI_PLUGIN_PROTOCOL = "pypi:"
if pyb_version == "${dist_version}":  # This is the case of PyB bootstrap
    PYB_VERSION = Version('0.0.1.dev0')
else:
    PYB_VERSION = Version(pyb_version)


class PluginLoader(object):
    def __init__(self, logger):
        self.logger = logger

    def load_plugin(self, project, name, version=None):
        pass


class BuiltinPluginLoader(PluginLoader):
    def load_plugin(self, project, name, version=None):
        self.logger.debug("Trying to load builtin plugin '%s'", name)
        builtin_plugin_name = "pybuilder.plugins.%s_plugin" % name

        plugin_module = _load_plugin(builtin_plugin_name, name)
        self.logger.debug("Found builtin plugin '%s'", builtin_plugin_name)
        return plugin_module


class ThirdPartyPluginLoader(PluginLoader):
    def load_plugin(self, project, name, version=None):
        thirdparty_plugin = name
        # Maybe we already installed this plugin from PyPI before
        if thirdparty_plugin.startswith(PYPI_PLUGIN_PROTOCOL):
            thirdparty_plugin = thirdparty_plugin.replace(PYPI_PLUGIN_PROTOCOL, "")
        self.logger.debug("Trying to load third party plugin '%s'", thirdparty_plugin)

        plugin_module = _load_plugin(thirdparty_plugin, name)
        self.logger.debug("Found third party plugin '%s'", thirdparty_plugin)
        return plugin_module


class DownloadingPluginLoader(ThirdPartyPluginLoader):
    def load_plugin(self, project, name, version=None):
        display_name = "%s%s" % (name, " version %s" % version if version else "")
        self.logger.info("Downloading missing plugin {0}".format(display_name))
        try:
            _install_external_plugin(name, version, self.logger)
            self.logger.info("Installed plugin {0}.".format(display_name))
        except MissingPluginException as e:
            self.logger.error("Could not install plugin {0}: {1}.".format(display_name, e))
            return None
        return ThirdPartyPluginLoader.load_plugin(self, project, name)


class DispatchingPluginLoader(PluginLoader):
    def __init__(self, logger, *loader):
        super(DispatchingPluginLoader, self).__init__(logger)
        self.loader = loader

    def load_plugin(self, project, name, version=None):
        last_problem = None
        for loader in self.loader:
            try:
                return loader.load_plugin(project, name)
            except MissingPluginException as e:
                last_problem = e
        raise last_problem


def _install_external_plugin(name, version, logger):
    if not name.startswith(PYPI_PLUGIN_PROTOCOL):
        message = "Only plugins starting with '{0}' are currently supported"
        raise MissingPluginException(name, message.format(PYPI_PLUGIN_PROTOCOL))
    plugin_name_on_pypi = name.replace(PYPI_PLUGIN_PROTOCOL, "")
    log_file = tempfile.NamedTemporaryFile(delete=False).name
    install_cmd = ['pip', 'install']
    if version:
        install_cmd += ['--upgrade', '--pre', plugin_name_on_pypi + str(version)]
    else:
        install_cmd += [plugin_name_on_pypi]
    result = execute_command(install_cmd,
                             log_file,
                             error_file_name=log_file,
                             shell=True)
    if result != 0:
        logger.error("The following pip error was encountered:\n" + "".join(read_file(log_file)))
        message = "Failed to install from PyPI".format(plugin_name_on_pypi)
        raise MissingPluginException(name, message)


def _load_plugin(plugin_module_name, plugin_name):
    try:
        __import__(plugin_module_name)
        plugin_module = sys.modules[plugin_module_name]
        _check_plugin_version(plugin_module, plugin_name)
        return plugin_module

    except ImportError as import_error:
        raise MissingPluginException(plugin_name, import_error)


def _check_plugin_version(plugin_module, plugin_name):
    if hasattr(plugin_module, "pyb_version") and plugin_module.pyb_version:
        required_pyb_version = SpecifierSet(plugin_module.pyb_version, True)
        if not required_pyb_version.contains(PYB_VERSION):
            raise IncompatiblePluginException(plugin_name, required_pyb_version, PYB_VERSION)
