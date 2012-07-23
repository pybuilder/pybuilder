#  This file is part of Python Builder
#   
#  Copyright 2011 The Python Builder Team
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
import sys

from pythonbuilder.errors import MissingPluginException

class PluginLoader (object):
    def __init__ (self, logger):
        self.logger = logger
        
    def load_plugin (self, project, name):
        pass
    
class BuiltinPluginLoader (PluginLoader):
    def load_plugin (self, project, name):
        # The parameter project is a required attribute due to inheritance. 
        # We need to tell pychecker to ignore it.
        __pychecker__ = 'unusednames=project'
        
        self.logger.debug("Trying to load builtin plugin '%s'", name)
        builtin_plugin_name = "pythonbuilder.plugins.%s_plugin" % name
        try:
            __import__(builtin_plugin_name)
            self.logger.debug("Found builtin plugin '%s'", builtin_plugin_name)
            return sys.modules[builtin_plugin_name] 
        except ImportError as import_error:
            raise MissingPluginException(name, import_error)
        
class DispatchingPluginLoader (PluginLoader):
    def __init__ (self, logger, *loader):
        super(DispatchingPluginLoader, self).__init__(logger)
        self.loader = loader
        
    def load_plugin (self, project, name):
        for loader in self.loader:
            try:
                return loader.load_plugin(project, name)
            except MissingPluginException:
                pass
        raise MissingPluginException(name)