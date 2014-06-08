#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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
import unittest
from mockito import mock, unstub, any, verify, when

import pybuilder
from pybuilder.plugins.python.test_plugin_helper import ReportsProcessor
from pybuilder.errors import BuildFailedException


class ReportsProcessorTests(unittest.TestCase):

    def setUp(self):
        self.reports_processor = ReportsProcessor(mock(), mock())
        self.reports_processor.process_reports([], mock())

    def tearDown(self):
        unstub()

    def test_should_raise_exception_when_not_all_tests_pass(self):

        self.reports_processor.tests_failed = 1

        self.assertRaises(
            BuildFailedException, self.reports_processor.write_report_and_ensure_all_tests_passed)

    def test_should_not_raise_exception_when_all_tests_pass(self):
        self.reports_processor.tests_failed = 0

        self.reports_processor.write_report_and_ensure_all_tests_passed()

    def test_should_write_report(self):
        when(pybuilder.plugins.python.test_plugin_helper).render_report(
            any()).thenReturn('rendered-report')

        self.reports_processor.write_report_and_ensure_all_tests_passed()

        verify(self.reports_processor.project).write_report(
            "integrationtest.json", 'rendered-report')

    def test_should_parse_reports(self):
        reports = [
            {'test': 'name1', 'test_file':
                'file1', 'success': False, 'time': 1},
            {'test': 'name2', 'test_file':
                'file2', 'success': False, 'time': 2},
            {'test': 'name3', 'test_file':
                'file3', 'success': True, 'time': 3},
            {'test': 'name4', 'test_file': 'file4', 'success': True, 'time': 4}
        ]
        self.reports_processor.process_reports(reports, mock())

        self.assertEqual(self.reports_processor.tests_failed, 2)
        self.assertEqual(self.reports_processor.tests_executed, 4)

    def test_should_create_test_report_with_attributes(self):
        mock_time = mock()
        when(mock_time).get_millis().thenReturn(42)

        self.reports_processor.process_reports([], mock_time)
        self.reports_processor.tests_failed = 4
        self.reports_processor.tests_executed = 42
        self.reports_processor.reports = ['a', 'b', 'c']

        self.assertEqual(self.reports_processor.test_report,
                         {
                             'num_of_tests': 42,
                             'success': False,
                             'tests': ['a', 'b', 'c'],
                             'tests_failed': 4,
                             'time': 42
                         }
                         )
