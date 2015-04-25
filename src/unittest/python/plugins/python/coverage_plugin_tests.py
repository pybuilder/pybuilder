from unittest import TestCase
from pybuilder.core import Project
# from mock import Mock, patch
# from logging import Logger
from pybuilder.plugins.python.coverage_plugin import (
    init_coverage_properties
    )


class CoveragePluginTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "coverage_threshold_warn": 70,
            "coverage_break_build": True,
            "coverage_reload_modules": True,
            "coverage_exceptions": [],
            "coverage_fork": False
        }

        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            init_coverage_properties(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(

                self.project.get_property(property_name),
                property_value)
