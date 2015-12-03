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
from pybuilder.core import use_plugin, before, task, init
from pybuilder.utils import assert_can_execute, execute_command

use_plugin("python.core")


@init
def depend_on_snakefood(project):
    project.plugin_depends_on("snakefood")


@before("render_snakefood_report")
def check_snakefood_available(logger):
    logger.debug("Checking availability of snakefood")
    assert_can_execute(("sfood", "-h"), "sfood", "plugin python.snakefood")
    logger.debug("snakefood has been found")


@before("render_snakefood_report")
def check_graphviz_available(logger):

    logger.debug("Checking availability of graphviz")
    assert_can_execute(("dot", "-V"), "graphviz", "plugin python.snakefood")
    logger.debug("graphviz has been found")


@task("render_snakefood_report", description="Renders a snakefood PDF to the reports directory.")
def render_snakefood_report(project, logger):
    logger.info("Executing snakefood on project sources")

    internal_report_file = project.expand_path("$dir_reports/snakefood-internal")
    external_report_file = project.expand_path("$dir_reports/snakefood-external")
    collect_dependencies(project, internal_report_file, external_report_file)

    logger.debug("Transforming snakefood graphs to graphviz")
    internal_graph_file = project.expand_path("$dir_reports/snakefood-internal.dot")
    external_graph_file = project.expand_path("$dir_reports/snakefood-external.dot")
    generate_graph(internal_report_file, internal_graph_file)
    generate_graph(external_report_file, external_graph_file)

    logger.debug("Rendering pdfs")
    internal_pdf_file = project.expand_path("$dir_reports/snakefood-internal.pdf")
    external_pdf_file = project.expand_path("$dir_reports/snakefood-external.pdf")
    generate_pdf(internal_graph_file, internal_pdf_file)
    logger.debug("Created {0}".format(internal_pdf_file))
    logger.debug("Created {0}".format(external_pdf_file))
    generate_pdf(external_graph_file, external_pdf_file)


def collect_dependencies(project, internal_report_file, external_report_file):
    source_dir = project.expand_path("$dir_source_main_python")
    internal_command = ["sfood", "--internal"]
    external_command = ["sfood", "--external"]

    execute_command(internal_command, internal_report_file, cwd=source_dir)
    execute_command(external_command, external_report_file, cwd=source_dir)


def generate_graph(report_file, graph_file):
    execute_command(["sfood-graph", report_file], graph_file)


def generate_pdf(graph_file, pdf_file):
    execute_command(["dot", "-Tpdf", graph_file], pdf_file)
