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

from pybuilder.ci_server_interaction import test_proxy_for
from pybuilder.errors import BuildFailedException
from pybuilder.utils import render_report


class ReportsProcessor(object):

    def __init__(self, project, logger):
        self.project = project
        self.logger = logger
        self.tests_failed = 0
        self.tests_executed = 0

    def process_reports(self, reports, total_time):
        self.reports = reports
        self.total_time = total_time
        for report in reports:
            if not report['success']:
                self.tests_failed += 1
            self.tests_executed += 1

    @property
    def test_report(self):
        return {
            "time": self.total_time.get_millis(),
            "success": self.tests_failed == 0,
            "num_of_tests": self.tests_executed,
            "tests_failed": self.tests_failed,
            "tests": self.reports
        }

    def write_report_and_ensure_all_tests_passed(self):
        self.project.write_report("integrationtest.json", render_report(self.test_report))
        self.logger.info("Executed %d integration tests.", self.tests_executed)
        if self.tests_failed:
            raise BuildFailedException("%d of %d integration tests failed." % (self.tests_failed, self.tests_executed))

    def report_to_ci_server(self, project):
        for report in self.reports:
            test_name = report['test']
            test_failed = report['success'] is not True
            with test_proxy_for(project).and_test_name('Integrationtest.%s' % test_name) as test:
                if test_failed:
                    test.fails(report['exception'])
