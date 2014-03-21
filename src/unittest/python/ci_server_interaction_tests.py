import unittest
from mock import patch, call

from pybuilder.core import Project
from pybuilder.ci_server_interaction import (test_proxy_for,
                                             TeamCityTestProxy,
                                             TestProxy)


class TestProxyTests(unittest.TestCase):

    def setUp(self):
        self.project = Project('basedir')

    def test_should_use_teamcity_proxy_if_project_property_is_set(self):
        self.project.set_property('teamcity_output', True)

        proxy = test_proxy_for(self.project)

        self.assertEquals(type(proxy), TeamCityTestProxy)

    def test_should_use_default_proxy_if_project_property_is_not_set(self):
        self.project.set_property('teamcity_output', False)

        proxy = test_proxy_for(self.project)

        self.assertEquals(type(proxy), TestProxy)

    def test_should_use_default_proxy_if_project_property_is_set_but_coverage_is_running(self):
        self.project.set_property('teamcity_output', True)
        self.project.set_property('__running_coverage', True)

        proxy = test_proxy_for(self.project)

        self.assertEquals(type(proxy), TestProxy)


class TeamCityProxyTests(unittest.TestCase):

    @patch('pybuilder.ci_server_interaction.flush_text_line')
    def test_should_output_happypath_test_for_teamcity(self, output):
        with TeamCityTestProxy().and_test_name('important-test'):
            pass

        self.assertEqual(output.call_args_list,
                         [
                             call("##teamcity[testStarted name='important-test']"),
                             call("##teamcity[testFinished name='important-test']")
                         ])

    @patch('pybuilder.ci_server_interaction.flush_text_line')
    def test_should_output_failed_test_for_teamcity(self, output):
        with TeamCityTestProxy().and_test_name('important-test') as test:
            test.fails('booom')

        self.assertEqual(output.call_args_list,
                         [
                             call("##teamcity[testStarted name='important-test']"),
                             call("##teamcity[testFailed name='important-test' message='See details' details='booom']"),
                             call("##teamcity[testFinished name='important-test']")
                         ])
