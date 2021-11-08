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

import logging
from os.path import normcase as nc

from pybuilder.core import init, use_plugin, finalize
from pybuilder.errors import BuildFailedException
from pybuilder.execution import ExecutionManager
from pybuilder.plugins.python._coverage_util import patch_coverage

use_plugin("python.core")
use_plugin("analysis")
use_plugin("python.coverage")


@init(environments="ci")
def init_coveralls_properties(project):
    project.plugin_depends_on("coveralls", "~=3.0")

    project.set_property_if_unset("coveralls_dry_run", False)
    project.set_property_if_unset("coveralls_report", False)
    project.set_property_if_unset("coveralls_token_required", True)


@finalize(environments="ci")
def finalize_coveralls(project, logger, reactor):
    em = reactor.execution_manager  # type: ExecutionManager

    if not em.is_task_in_current_execution_plan("coverage"):
        return

    patch_coverage()

    from coveralls.api import Coveralls, CoverallReporter, CoverallsException
    from coverage import coverage, files

    class PybCoveralls(Coveralls):
        def get_coverage(self):
            coverage_config = project.get_property("__coverage_config")

            workman = coverage(**coverage_config)
            workman.load()

            if hasattr(workman, '_harvest_data'):
                workman._harvest_data()  # pylint: disable=W0212
            else:
                workman.get_data()

            return CoverallReporter(workman, workman.config).coverage

    coveralls_logger = logging.getLogger("coveralls")
    coveralls_logger.addHandler(logger)

    try:
        dry_run = project.get_property("coveralls_dry_run")
        report = project.get_property("coveralls_report")
        token_required = project.get_property("coveralls_token_required") and not dry_run and not report

        old_relative_dir = files.RELATIVE_DIR
        files.RELATIVE_DIR = nc(project.expand_path(project.get_property("coverage_source_path")))
        try:
            pyb_coveralls = PybCoveralls(token_required=token_required)
            try:
                staging = False
                if report:
                    report_file = project.expand_path("$dir_reports", "%s.coveralls.json" % project.name)
                    pyb_coveralls.save_report(report_file)
                    logger.info("Written Coveralls report into %r", report_file)
                    staging = True

                if dry_run:
                    pyb_coveralls.wear(dry_run=True)
                    logger.info("Coveralls dry-run coverage test has been completed!")
                    staging = True

                if staging:
                    return

                try:
                    report_result = pyb_coveralls.wear()
                except CoverallsException as e:
                    # https://github.com/TheKevJames/coveralls-python/issues/252
                    if (pyb_coveralls.config["service_name"] == "github-actions" and
                            hasattr(e.__cause__, "response") and
                            hasattr(e.__cause__.response, "status_code") and
                            e.__cause__.response.status_code == 422):
                        pyb_coveralls = PybCoveralls(token_required=token_required, service_name="github")
                        report_result = pyb_coveralls.wear()
                    else:
                        raise

                logger.debug("Coveralls result: %r", report_result)
                logger.info("Coveralls coverage successfully submitted! %s @ %s",
                            report_result["message"],
                            report_result["url"])
            except CoverallsException as e:
                raise BuildFailedException("Failed to upload Coveralls coverage: %s", e)
        finally:
            files.RELATIVE_DIR = old_relative_dir
    finally:
        coveralls_logger.removeHandler(logger)
