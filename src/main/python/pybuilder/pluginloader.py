#   -*- coding: utf-8 -*-
#
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

"""
    The PyBuilder pluginloader module.
    Provides a mechanism to load PyBuilder plugins.
"""

import sys
import tempfile

from pybuilder.errors import MissingPluginException
from pybuilder.utils import execute_command, read_file


PYPI_PLUGIN_PROTOCOL = "pypi:"


class PluginLoader (object):

    def __init__(self, logger):
        self.logger = logger

    def load_plugin(self, project, name):
        pass


class BuiltinPluginLoader(PluginLoader):

    def load_plugin(self, project, name):
        self.logger.debug("Trying to load builtin plugin '%s'", name)
        builtin_plugin_name = "pybuilder.plugins.%s_plugin" % name
        try:
            __import__(builtin_plugin_name)
            self.logger.debug("Found builtin plugin '%s'", builtin_plugin_name)
            return sys.modules[builtin_plugin_name]
        except ImportError as import_error:
            raise MissingPluginException(name, import_error)


class ThirdPartyPluginLoader(PluginLoader):

    def load_plugin(self, project, name):
        thirdparty_plugin = name
        # Maybe we already installed this plugin from PyPI before
        if thirdparty_plugin.startswith(PYPI_PLUGIN_PROTOCOL):
            thirdparty_plugin = thirdparty_plugin.replace(PYPI_PLUGIN_PROTOCOL, "")
        self.logger.debug("Trying to load third party plugin '%s'", thirdparty_plugin)

        try:
            __import__(thirdparty_plugin)
            self.logger.debug("Found third party plugin '%s'", thirdparty_plugin)
            return sys.modules[thirdparty_plugin]
        except ImportError as import_error:
            raise MissingPluginException(name, import_error)


class DownloadingPluginLoader(ThirdPartyPluginLoader):

    def load_plugin(self, project, name):
        self.logger.info("Downloading missing plugin {0}".format(name))
        try:
            _install_external_plugin(name, self.logger)
            self.logger.info("Installed plugin {0}.".format(name))
        except MissingPluginException as e:
            self.logger.error("Could not install plugin {0}: {1}.".format(name, e))
            return None
        return ThirdPartyPluginLoader.load_plugin(self, project, name)


class DispatchingPluginLoader(PluginLoader):

    def __init__(self, logger, *loader):
        super(DispatchingPluginLoader, self).__init__(logger)
        self.loader = loader

    def load_plugin(self, project, name):
        last_problem = None
        for loader in self.loader:
            try:
                return loader.load_plugin(project, name)
            except MissingPluginException as e:
                last_problem = e
        raise last_problem


def _install_external_plugin(name, logger):
    if not name.startswith(PYPI_PLUGIN_PROTOCOL):
        message = "Only plugins starting with '{0}' are currently supported"
        raise MissingPluginException(name, message.format(PYPI_PLUGIN_PROTOCOL))
    plugin_name_on_pypi = name.replace(PYPI_PLUGIN_PROTOCOL, "")
    log_file = tempfile.NamedTemporaryFile(delete=False).name
    result = execute_command(
        'pip install {0}'.format(plugin_name_on_pypi),
        log_file,
        error_file_name=log_file,
        shell=True)
    if result != 0:
        logger.error("The following pip error was encountered:\n" + "".join(read_file(log_file)))
        message = "Failed to install from PyPI".format(plugin_name_on_pypi)
        raise MissingPluginException(name, message)
