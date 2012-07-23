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
from pythonbuilder.core import use_plugin, after, task
from pythonbuilder.utils import discover_files, assert_can_execute, execute_command

use_plugin("python.core")
use_plugin("analysis")

@after("prepare")
def check_snakefood_available (logger):
    logger.debug("Checking availability of snakefood")
    assert_can_execute(("sfood", "-h"), "sfood", "plugin python.snakefood")
    logger.debug("snakefood has been found")

    logger.debug("Checking availability of graphviz")
    assert_can_execute(("dot", "-V"), "graphviz", "plugin python.snakefood")
    logger.debug("graphviz has been found")

@task("analyze")
def execute_snakefood (project, logger):
    logger.info("Executing snakefood on project sources")

    report_file = project.expand_path("$dir_reports/snakefood")
    collect_dependencies(project, report_file)

    logger.debug("Transforming snakefood graph to graphviz")
    graph_file = project.expand_path("$dir_reports/snakefood.dot")
    generate_graph(report_file, graph_file)

    logger.debug("Rendering pdf")
    pdf_file = project.expand_path("$dir_reports/snakefood.pdf")
    generate_pdf(graph_file, pdf_file)

def collect_dependencies (project, report_file):
    source_dir = project.expand_path("$dir_source_main_python")
    command = ["sfood", "--internal"]
    for source_file in discover_files(source_dir, ".py"):
        command.append(source_file)
    
    env = {"PYTHONPATH":source_dir}
    execute_command(command, report_file, env=env)
    
def generate_graph (report_file, graph_file):
    execute_command(["sfood-graph", report_file], graph_file)
    
def generate_pdf(graph_file, pdf_file):
    execute_command(["dot", "-Tpdf", graph_file], pdf_file)        