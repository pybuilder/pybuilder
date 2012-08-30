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

from django.core.management import execute_manager

from pythonbuilder.core import use_plugin, task
from pythonbuilder.errors import PythonbuilderException

use_plugin("python.core")

@task
def django_run_server (project, logger):
    django_module = project.get_mandatory_property("django_module")
    
    logger.info("Running Django development server for %s", django_module)
    
    module = "%s.settings" % django_module
    sys.path.append(project.expand_path("$dir_source_main_python"))
    try:
        __import__(module)
    except ImportError as e:
        raise PythonbuilderException("Missing settings module: " + str(e))
    
    execute_manager(sys.modules[module], ["", "runserver"])
