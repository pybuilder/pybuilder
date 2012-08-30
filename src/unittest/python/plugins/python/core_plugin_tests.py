import unittest

from pythonbuilder.plugins.python.core_plugin import init_python_directories
from pythonbuilder.plugins.python.core_plugin import DISTRIBUTION_PROPERTY, PYTHON_SOURCES_PROPERTY, SCRIPTS_SOURCES_PROPERTY, SCRIPTS_TARGET_PROPERTY

from pythonbuilder.core import Project

class InitPythonDirectoriesTest (unittest.TestCase):
    def setUp(self):
        self.project = Project(".")
        
    def test_should_set_python_sources_property(self):
        init_python_directories(self.project)
        self.assertEquals("src/main/python", self.project.get_property(PYTHON_SOURCES_PROPERTY, "caboom"))
        
    def test_should_set_scripts_sources_property(self):
        init_python_directories(self.project)
        self.assertEquals("src/main/scripts", self.project.get_property(SCRIPTS_SOURCES_PROPERTY, "caboom"))
        
    def test_should_set_dist_scripts_property(self):
        init_python_directories(self.project)
        self.assertEquals(None, self.project.get_property(SCRIPTS_TARGET_PROPERTY, "caboom"))

    def test_should_set_dist_property(self):
        init_python_directories(self.project)
        self.assertEquals("$dir_target/dist/.-1.0-SNAPSHOT", self.project.get_property(DISTRIBUTION_PROPERTY, "caboom"))
