from unittest import TestCase
from pybuilder.core import Project
from test_utils import Mock
from pybuilder.plugins.python.pytype_plugin import initialize_pytype_plugin


class PytypePluginInitializationTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_set_dependency(self):
        mock_project = Mock(Project)
        initialize_pytype_plugin(mock_project)
        mock_project.plugin_depends_on.assert_called_with("pytype")

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        self.project.set_property("pytype_break_build", True)
        initialize_pytype_plugin(self.project)

        self.assertEqual(self.project.get_property("pytype_break_build"), True)
