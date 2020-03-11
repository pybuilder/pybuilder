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

import os
import sys

from pybuilder.core import use_plugin, task
from pybuilder.errors import PyBuilderException

use_plugin("python.core")


@task
def django_run_server(project, logger):
    django_module_name = project.get_mandatory_property("django_module")

    logger.info("Running Django development server for %s", django_module_name)

    settings_module_name = "{0}.settings".format(django_module_name)
    sys.path.append(project.expand_path("$dir_source_main_python"))
    try:
        __import__(settings_module_name)
    except ImportError as e:
        raise PyBuilderException("Error when importing settings module: " + str(e))

    from django import VERSION as DJANGO_VERSION
    if DJANGO_VERSION < (1, 4, 0):
        from django.core.management import execute_manager
        execute_manager(sys.modules[settings_module_name], ["", "runserver"])
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module_name)
        from django.core.management import execute_from_command_line
        execute_from_command_line(["", "runserver"])
