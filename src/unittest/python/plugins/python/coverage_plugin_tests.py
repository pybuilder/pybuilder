from unittest import TestCase
from pybuilder.core import Project
from pybuilder.plugins.python.coverage_plugin import (
    init_coverage_properties
)


class CoveragePluginTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "coverage_threshold_warn": 120,
            "coverage_break_build": False,
            "coverage_reload_modules": False,
            "coverage_exceptions": ["foo"],
            "coverage_fork": True
        }

        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            init_coverage_properties(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(
                self.project.get_property("coverage_threshold_warn"), 120)
            self.assertEquals(
                self.project.get_property("coverage_break_build"), False)
            self.assertEquals(
                self.project.get_property("coverage_reload_modules"), False)
            self.assertEquals(
                self.project.get_property("coverage_exceptions"), ["foo"])
            self.assertEquals(
                self.project.get_property("coverage_fork"), True)
