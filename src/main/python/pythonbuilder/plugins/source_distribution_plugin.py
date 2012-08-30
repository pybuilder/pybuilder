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
import os
import shutil

from pythonbuilder.core import init, task, use_plugin

use_plugin("core")

@init
def init_source_distribution (project):
    project.set_property_if_unset("dir_source_dist", 
                                  "$dir_target/dist/%s-%s-src" % (project.name,
                                                                  project.version))
    project.set_property_if_unset("source_dist_ignore_patterns",
                                  [ "*.pyc", ".hg*", ".svn", ".CVS"]) 

@task
def build_source_distribution (project, logger):
    dist = project.expand_path("$dir_source_dist")
    logger.info("Building source distribution in %s", dist)
    
    if os.path.exists(dist):
        shutil.rmtree(dist)
        
    ignore_patterns = ["target"]
    configured_patterns = project.get_property("source_dist_ignore_patterns")
    if configured_patterns:
        ignore_patterns += configured_patterns
        
    shutil.copytree(project.basedir, 
                    dist,
                    ignore=shutil.ignore_patterns(*ignore_patterns))