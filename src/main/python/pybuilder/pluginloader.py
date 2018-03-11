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
from traceback import format_exc

from pybuilder import __version__ as pyb_version
# Plugin install_dependencies_plugin can reload pip_common and pip_utils. Do not use from ... import ...
from pybuilder import pip_utils, pip_common
from pybuilder.errors import (MissingPluginException,
                              IncompatiblePluginException,
                              UnspecifiedPluginNameException,
                              )
from pybuilder.utils import read_file

PYPI_PLUGIN_PROTOCOL = "pypi:"
VCS_PLUGIN_PROTOCOL = "vcs:"

if pyb_version == "${dist_version}":  # This is the case of PyB bootstrap
    PYB_VERSION = pip_common.Version('0.0.1.dev0')
else:
    PYB_VERSION = pip_common.Version(pyb_version)


class PluginLoader(object):
    def __init__(self, logger):
        self.logger = logger

    def can_load(self, project, name, version=None, plugin_module_name=None):
        pass

    def load_plugin(self, project, name, version=None, plugin_module_name=None):
        pass


class BuiltinPluginLoader(PluginLoader):
    def can_load(self, project, name, version=None, plugin_module_name=None):
        return ":" not in name

    def load_plugin(self, project, name, version=None, plugin_module_name=None):
        self.logger.debug("Trying to load builtin plugin '%s'", name)
        builtin_plugin_name = plugin_module_name or "pybuilder.plugins.%s_plugin" % name

        try:
            plugin_module = _load_plugin(builtin_plugin_name, name)
        except MissingPluginException as e:
            self.logger.debug("Builtin plugin %s failed to load: %s", builtin_plugin_name, e.message)
            raise

        self.logger.debug("Found builtin plugin '%s'", builtin_plugin_name)
        return plugin_module


class DownloadingPluginLoader(PluginLoader):
    def can_load(self, project, name, version=None, plugin_module_name=None):
        return name.startswith(PYPI_PLUGIN_PROTOCOL) or name.startswith(VCS_PLUGIN_PROTOCOL) or ":" not in name

    def load_plugin(self, project, name, version=None, plugin_module_name=None):
        display_name = _plugin_display_name(name, version, plugin_module_name)

        update_plugin = False
        force_reinstall = False

        thirdparty_plugin = name
        # Maybe we already installed this plugin from PyPI before
        if thirdparty_plugin.startswith(PYPI_PLUGIN_PROTOCOL):
            thirdparty_plugin = thirdparty_plugin.replace(PYPI_PLUGIN_PROTOCOL, "")
            update_plugin = pip_utils.should_update_package(version)
        elif thirdparty_plugin.startswith(VCS_PLUGIN_PROTOCOL):
            if not plugin_module_name:
                raise UnspecifiedPluginNameException(name)
            thirdparty_plugin = plugin_module_name
            force_reinstall = True

        # This is done before we attempt to load a plugin regardless of whether it can be loaded or not
        if update_plugin or force_reinstall:
            self.logger.info("Downloading or updating plugin {0}".format(display_name))
            try:
                _install_external_plugin(project, name, version, self.logger, plugin_module_name, update_plugin,
                                         force_reinstall)
                self.logger.info("Installed or updated plugin {0}.".format(display_name))
            except MissingPluginException as e:
                self.logger.error("Could not install or upgrade plugin {0}: {1}.".format(display_name, e))

        # Now let's try to load the plugin
        try:
            return self._load_installed_plugin(thirdparty_plugin, name)
        except MissingPluginException:
            if update_plugin or force_reinstall:
                # If we already tried installing - fail fast
                raise
            self.logger.warn("Missing plugin {0}".format(display_name))

        # We have failed to update or to load a plugin without a previous installation
        self.logger.info("Downloading plugin {0}".format(display_name))
        try:
            _install_external_plugin(project, name, version, self.logger, plugin_module_name)
            self.logger.info("Installed plugin {0}.".format(display_name))
        except MissingPluginException as e:
            self.logger.error("Could not install plugin {0}: {1}.".format(display_name, e))
            raise

        # After we have failed to update or load
        return self._load_installed_plugin(thirdparty_plugin, name)

    def _load_installed_plugin(self, thirdparty_plugin, name):
        self.logger.debug("Trying to load third party plugin '%s'", thirdparty_plugin)
        plugin_module = _load_plugin(thirdparty_plugin, name)
        self.logger.debug("Found third party plugin '%s'", thirdparty_plugin)
        return plugin_module


class DispatchingPluginLoader(PluginLoader):
    def __init__(self, logger, *loaders):
        super(DispatchingPluginLoader, self).__init__(logger)
        self._loaders = loaders

    def can_load(self, project, name, version=None, plugin_module_name=None):
        for loader in self._loaders:
            if loader.can_load(project, name, version, plugin_module_name):
                return True
        return False

    def load_plugin(self, project, name, version=None, plugin_module_name=None):
        last_problem = None
        for loader in self._loaders:
            if loader.can_load(project, name, version, plugin_module_name):
                try:
                    return loader.load_plugin(project, name, version, plugin_module_name)
                except MissingPluginException as e:
                    last_problem = e
        if last_problem:
            raise last_problem
        else:
            raise MissingPluginException(_plugin_display_name(name, version, plugin_module_name),
                                         "no plugin loader was able to load the plugin specified")


def _install_external_plugin(project, name, version, logger, plugin_module_name, upgrade=False, force_reinstall=False):
    if not name.startswith(PYPI_PLUGIN_PROTOCOL) and not name.startswith(VCS_PLUGIN_PROTOCOL):
        message = "Only plugins starting with '{0}' are currently supported"
        raise MissingPluginException(name, message.format((PYPI_PLUGIN_PROTOCOL, VCS_PLUGIN_PROTOCOL)))

    if name.startswith(PYPI_PLUGIN_PROTOCOL):
        pip_package = name.replace(PYPI_PLUGIN_PROTOCOL, "")
        if version:
            pip_package += str(version)
            upgrade = True
    elif name.startswith(VCS_PLUGIN_PROTOCOL):
        pip_package = name.replace(VCS_PLUGIN_PROTOCOL, "")
        force_reinstall = True

    with tempfile.NamedTemporaryFile(mode="w+t") as log_file:
        result = pip_utils.pip_install(
            install_targets=pip_package,
            index_url=project.get_property("install_dependencies_index_url"),
            extra_index_url=project.get_property("install_dependencies_extra_index_url"),
            trusted_host=project.get_property("install_dependencies_trusted_host"),
            upgrade=upgrade,
            force_reinstall=force_reinstall,
            logger=logger,
            outfile_name=log_file,
            error_file_name=log_file,
            cwd=".")
        if result != 0:
            logger.error("The following pip error was encountered:\n" + "".join(read_file(log_file)))
            message = "Failed to install plugin from {0}".format(pip_package)
            raise MissingPluginException(name, message)


def _plugin_display_name(name, version, plugin_module_name):
    return "%s%s%s" % (name, " version %s" % version if version else "",
                       ", module name '%s'" % plugin_module_name if plugin_module_name else "")


def _load_plugin(plugin_module_name, plugin_name):
    try:
        __import__(plugin_module_name)
        plugin_module = sys.modules[plugin_module_name]
        _check_plugin_version(plugin_module, plugin_name)
        return plugin_module

    except ImportError:
        raise MissingPluginException(plugin_name, format_exc())


def _check_plugin_version(plugin_module, plugin_name):
    if hasattr(plugin_module, "pyb_version") and plugin_module.pyb_version:
        if not pip_utils.version_satisfies_spec(plugin_module.pyb_version, PYB_VERSION):
            raise IncompatiblePluginException(plugin_name, plugin_module.pyb_version, PYB_VERSION)
