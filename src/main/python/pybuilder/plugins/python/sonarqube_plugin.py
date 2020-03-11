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

from os.path import join

from pybuilder.core import task, init, before, depends
from pybuilder.errors import BuildFailedException
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder


@before("run_sonar_analysis")
def check_sonar_scanner_availability(project, reactor):
    reactor.python_env_registry["pybuilder"].verify_can_execute(["sonar-scanner", "-h"], "sonar-scanner",
                                                                "plugin python.sonarqube")


@init
def initialize_sonarqube_plugin(project):
    project.set_property_if_unset("sonarqube_project_key", project.name)
    project.set_property_if_unset("sonarqube_project_name", project.name)


@task("run_sonar_analysis", description="Launches sonar-scanner for analysis.")
@depends("analyze")
def run_sonar_analysis(project, logger, reactor):
    sonar_scanner = build_sonar_scanner(project, reactor)

    result = sonar_scanner.run(project.expand_path("$dir_reports/sonar-scanner"))

    if result.exit_code != 0:
        logger.error(
            "sonar-scanner exited with code {exit_code}. See {reports_dir} for more information.".format(
                exit_code=result.exit_code,
                reports_dir=project.expand_path("$dir_reports")))

        if project.get_property("verbose"):
            logger.error("Contents of {0}:".format(result.error_report_file))
            logger.error("\n".join(result.error_report_lines))

        raise BuildFailedException("Sonar analysis failed.")


def build_sonar_scanner(project, reactor):
    return (
        SonarCommandBuilder("sonar-scanner", project, reactor).set_sonar_key(
            "sonar.projectKey").to_property_value("sonarqube_project_key").set_sonar_key(
            "sonar.projectName").to_property_value("sonarqube_project_name").set_sonar_key(
            "sonar.projectVersion").to(project.version).set_sonar_key(
            "sonar.sources").to_property_value("dir_source_main_python").set_sonar_key(
            "sonar.python.coverage.reportPath").to(join(project.get_property("dir_target"),
                                                        "reports",
                                                        "coverage*.xml"))
    )


class SonarCommandBuilder(ExternalCommandBuilder):

    def set_sonar_key(self, key):
        self.key = key
        return self

    def to(self, value):
        self.use_argument("-D{key}={value}".format(key=self.key, value=value))
        return self

    def to_property_value(self, property_name):
        return self.to(self.project.get_property(property_name))
