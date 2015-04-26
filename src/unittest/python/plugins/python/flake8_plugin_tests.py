from unittest import TestCase
from pybuilder.core import Project
from mock import Mock
from pybuilder.plugins.python.flake8_plugin import initialize_flake8_plugin


class FlakePluginInitializationTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_set_dependency(self):
        mock_project = Mock(Project)
        initialize_flake8_plugin(mock_project)
        mock_project.build_depends_on.assert_called_with('flake8')

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "flake8_break_build": False,
            "flake8_max_line_length": 120,
            "flake8_exclude_patterns": None,
            "flake8_include_test_sources": False,
            "flake8_include_scripts": False
            }
        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            initialize_flake8_plugin(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(

                self.project.get_property(property_name),
                property_value)
