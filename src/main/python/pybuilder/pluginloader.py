#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2020 PyBuilder Team
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
from traceback import format_exc

from pybuilder import __version__ as pyb_version
from pybuilder.core import PluginDef
from pybuilder.errors import (MissingPluginException,
                              IncompatiblePluginException,
                              BuildFailedException
                              )
from pybuilder.pip_common import Version
from pybuilder.pip_utils import (version_satisfies_spec
                                 )
from pybuilder.utils import as_list

if pyb_version == "${dist_version}":  # This is the case of PyB bootstrap
    PYB_VERSION = Version('0.0.1.dev0')
else:
    PYB_VERSION = Version(pyb_version)


class PluginLoader(object):
    def __init__(self, logger):
        self.logger = logger

    def can_load(self, project, plugin_def):
        pass

    def load_plugin(self, project, plugin_defs):
        pass

    def install_plugin(self, project, plugin_defs):
        pass


class BuiltinPluginLoader(PluginLoader):
    def can_load(self, reactor, plugin_def):
        return ":" not in plugin_def.name

    def load_plugin(self, reactor, plugin_defs):
        candidates = []
        if plugin_defs.plugin_module_name:
            candidates.append(plugin_defs.plugin_module_name)
        else:
            candidates.append("pybuilder.plugins.%s_plugin" % plugin_defs.name)
            candidates.append(plugin_defs.name)

        last_problem = None
        for candidate in candidates:
            self.logger.debug("Trying to load direct plugin %r, module %r", plugin_defs.name, candidate)
            try:
                plugin_module = _load_plugin(candidate, plugin_defs.name)
                self.logger.debug("Found direct plugin %r, module %r", plugin_defs.name, candidate)
                return plugin_module
            except MissingPluginException as e:
                self.logger.debug("Direct plugin %r, module %r failed to load: %s", plugin_defs.name,
                                  candidate,
                                  e.message)
                last_problem = e

        if last_problem:
            raise last_problem


class DownloadingPluginLoader(PluginLoader):
    def can_load(self, reactor, plugin_def):
        return (plugin_def.name.startswith(PluginDef.PYPI_PLUGIN_PROTOCOL) or
                plugin_def.name.startswith(PluginDef.VCS_PLUGIN_PROTOCOL))

    def install_plugin(self, reactor, plugin_defs):
        plugin_defs = as_list(plugin_defs)
        pip_batch = []

        for plugin_def in plugin_defs:
            self._check_plugin_def_type(plugin_def)
            display_name = str(plugin_def)

            self.logger.info("Installing or updating plugin %r", display_name)

            pip_batch.append(plugin_def.dependency)

        try:
            reactor.pybuilder_venv.install_dependencies(pip_batch, package_type="plugin")
        except BuildFailedException as e:
            self.logger.warn(e.message)

    def load_plugin(self, reactor, plugin_def):
        plugin_module_name = plugin_def.plugin_module_name or plugin_def.name
        self.logger.debug("Trying to load third party plugin %r, module %r", plugin_def.name, plugin_module_name)
        plugin_module = _load_plugin(plugin_module_name, plugin_def.name)
        self.logger.debug("Found third party plugin %r, module %r", plugin_def.name, plugin_module_name)
        return plugin_module

    def _check_plugin_def_type(self, plugin_def):
        if (not plugin_def.name.startswith(PluginDef.PYPI_PLUGIN_PROTOCOL) and
                not plugin_def.name.startswith(PluginDef.VCS_PLUGIN_PROTOCOL)):
            message = "Only plugins starting with '{0}' are currently supported"
            raise MissingPluginException(plugin_def, message.format(
                (PluginDef.PYPI_PLUGIN_PROTOCOL, PluginDef.VCS_PLUGIN_PROTOCOL)))


class DispatchingPluginLoader(PluginLoader):
    def __init__(self, logger, *loaders):
        super(DispatchingPluginLoader, self).__init__(logger)
        self._loaders = loaders

    def can_load(self, reactor, plugin_def):
        for loader in self._loaders:
            if loader.can_load(reactor, plugin_def):
                return True
        return False

    def install_plugin(self, reactor, plugin_defs):
        loader_plugins = {}
        plugin_defs = as_list(plugin_defs)

        for loader in self._loaders:
            loader_plugins[loader] = []

        for plugin_def in plugin_defs:
            loader_found = False
            for loader in self._loaders:
                if loader.can_load(reactor, plugin_def):
                    loader_plugins[loader].append(plugin_def)
                    loader_found = True
                    break
            if not loader_found:
                raise MissingPluginException(plugin_def,
                                             "no plugin loader was able to load the plugin specified")

        for loader, plugin_defs in loader_plugins.items():
            loader.install_plugin(reactor, plugin_defs)

    def load_plugin(self, project, plugin_def):
        last_problem = None

        for loader in self._loaders:
            if loader.can_load(project, plugin_def):
                try:
                    return loader.load_plugin(project, plugin_def)
                except MissingPluginException as e:
                    last_problem = e

        if last_problem:
            raise last_problem
        else:
            raise MissingPluginException(plugin_def,
                                         "no plugin loader was able to load the plugin specified")


def _load_plugin(plugin_module_name, plugin_name):
    try:
        __import__(plugin_module_name)
        plugin_module = sys.modules[plugin_module_name]
        _check_plugin_version(plugin_module, plugin_name)
        return plugin_module

    except ImportError:
        raise MissingPluginException("plugin %r, module %r" % (plugin_name, plugin_module_name), format_exc())


def _check_plugin_version(plugin_module, plugin_name):
    if hasattr(plugin_module, "pyb_version") and plugin_module.pyb_version:
        if not version_satisfies_spec(plugin_module.pyb_version, PYB_VERSION):
            raise IncompatiblePluginException(plugin_name, plugin_module.pyb_version, PYB_VERSION)
