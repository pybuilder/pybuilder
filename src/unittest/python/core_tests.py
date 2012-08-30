#  This file is part of Python Builder
#   
#  Copyright 2011 The Python Builder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import os
import unittest 

from mockito import when, verify, unstub

from pythonbuilder.core import Project, Logger
from pythonbuilder.errors import MissingPropertyException 

class ProjectTest (unittest.TestCase):
    def setUp (self):
        self.project = Project(basedir="/imaginary", name="Unittest")
    
    def test_should_pick_directory_name_for_project_name_when_name_is_not_given (self):
        try:
            when(os.path).basename("/imaginary").thenReturn("imaginary")
            
            project = Project(basedir="/imaginary")
            
            self.assertEquals("imaginary", project.name)
            verify(os.path).basename("/imaginary")
        finally:
            unstub()
    
    def test_get_property_should_return_default_value_when_property_is_not_set (self):
        self.assertEquals("spam", self.project.get_property("spam", "spam"))

    def test_get_property_should_return_property_value_when_property_is_set (self):
        self.project.set_property("spam", "eggs")
        self.assertEquals("eggs", self.project.get_property("spam", "spam"))

    def test_has_property_should_return_false_when_property_is_not_set (self):
        self.assertFalse(self.project.has_property("spam"))

    def test_has_property_should_return_true_when_property_is_set (self):
        self.project.set_property("spam", "eggs")
        self.assertTrue(self.project.has_property("spam"))
        
    def test_set_property_if_unset_should_set_property_when_property_is_not_set (self):
        self.project.set_property_if_unset("spam", "spam")
        self.assertEquals("spam", self.project.get_property("spam"))

    def test_set_property_if_unset_should_not_set_property_when_property_is_already_set (self):
        self.project.set_property("spam", "eggs")
        self.project.set_property_if_unset("spam", "spam")
        self.assertEquals("eggs", self.project.get_property("spam"))
    
    def test_expand_should_raise_exception_when_property_is_not_set (self):
        self.assertRaises(MissingPropertyException, self.project.expand, "$spam")

    def test_expand_should_return_expanded_string_when_property_is_set (self):
        self.project.set_property("spam", "eggs")
        self.assertEquals("eggs", self.project.expand("$spam"))

    def test_expand_should_return_expanded_string_when_two_properties_are_found_and_set (self):
        self.project.set_property("spam", "spam")
        self.project.set_property("eggs", "eggs")
        self.assertEquals("spam and eggs", self.project.expand("$spam and $eggs"))
        
    def test_expand_should_expand_property_with_value_being_an_property_expression (self):
        self.project.set_property("spam", "spam")
        self.project.set_property("eggs", "$spam")
        self.assertEquals("spam", self.project.expand("$eggs"))

    def test_expand_should_raise_exception_when_first_expansion_leads_to_property_reference_and_property_is_undefined (self):
        self.project.set_property("eggs", "$spam")
        self.assertRaises(MissingPropertyException, self.project.expand, "$eggs")
        
    def test_expand_path_should_return_expanded_path (self):
        self.project.set_property("spam", "spam")
        self.project.set_property("eggs", "eggs")
        self.assertEquals(os.path.join("/imaginary", "spam", "eggs"),
                          self.project.expand_path("$spam/$eggs"))

    def test_expand_path_should_return_expanded_path_and_additional_parts_when_additional_parts_are_given (self):
        self.project.set_property("spam", "spam")
        self.project.set_property("eggs", "eggs")
        self.assertEquals(os.path.join("/imaginary", "spam", "eggs", "foo", "bar"),
                          self.project.expand_path("$spam/$eggs", "foo", "bar"))
        
    def test_should_raise_exception_when_getting_mandatory_propert_and_property_is_not_found (self):
        self.assertRaises(MissingPropertyException, 
                          self.project.get_mandatory_property, "i_dont_exist")

    def test_should_return_property_value_when_getting_mandatory_propert_and_property_exists (self):
        self.project.set_property("spam", "spam")
        self.assertEquals("spam", self.project.get_mandatory_property("spam"))
        
    def test_should_add_runtime_dependency_with_name_only (self):
        self.project.depends_on("spam")
        self.assertEquals(1, len(self.project.dependencies))
        self.assertEquals("spam", self.project.dependencies[0].name)
        self.assertEquals(None, self.project.dependencies[0].version)

    def test_should_add_dependency_with_name_and_version (self):
        self.project.depends_on("spam", "0.7")
        self.assertEquals(1, len(self.project.dependencies))
        self.assertEquals("spam", self.project.dependencies[0].name)
        self.assertEquals("0.7", self.project.dependencies[0].version)

    def test_should_add_dependency_with_name_and_version_only_once (self):
        self.project.depends_on("spam", "0.7")
        self.project.depends_on("spam", "0.7")
        self.assertEquals(1, len(self.project.dependencies))
        self.assertEquals("spam", self.project.dependencies[0].name)
        self.assertEquals("0.7", self.project.dependencies[0].version)
        
class ProjectManifestTests (unittest.TestCase):
    def setUp (self):
        self.project = Project(basedir="/imaginary", name="Unittest")
    
    def test_should_raise_exception_when_given_glob_pattern_is_none (self):
        self.assertRaises(ValueError, self.project._manifest_include, None)
        
    def test_should_raise_exception_when_given_glob_pattern_is_empty_string (self):
        self.assertRaises(ValueError, self.project._manifest_include, "       \n")
        
    def test_should_add_filename_to_list_of_included_files (self):
        self.project._manifest_include("spam")
        self.assertEquals(["spam"], self.project.manifest_included_files)
        
    def test_should_add_filenames_in_correct_order_to_list_of_included_files (self):
        self.project._manifest_include("spam")
        self.project._manifest_include("egg")
        self.project._manifest_include("yadt")
        self.assertEquals(["spam", "egg", "yadt"], self.project.manifest_included_files)


class ProjectPackageDataTests (unittest.TestCase):
    def setUp (self):
        self.project = Project(basedir="/imaginary", name="Unittest")
    
    def test_should_raise_exception_when_package_name_not_given (self):
        self.assertRaises(ValueError, self.project.include_file, None, "spam")
        
    def test_should_raise_exception_when_filename_not_given (self):
        self.assertRaises(ValueError, self.project.include_file, "my_package", None)

    def test_should_raise_exception_when_package_name_is_empty_string (self):
        self.assertRaises(ValueError, self.project.include_file, "    \n", "spam")
        
    def test_should_raise_exception_when_filename_is_empty_string (self):
        self.assertRaises(ValueError, self.project.include_file, "eggs", "\t    \n")
        
    def test_should_package_data_dictionary_is_empty (self):
        self.assertEquals({}, self.project.package_data)
        
    def test_should_add_filename_to_list_of_included_files_for_package_spam (self):
        self.project.include_file("spam", "eggs")
        
        self.assertEquals({"spam": ["eggs"]}, self.project.package_data)

    def test_should_add_two_filenames_to_list_of_included_files_for_package_spam (self):
        self.project.include_file("spam", "eggs")
        self.project.include_file("spam", "ham")
        
        self.assertEquals({"spam": ["eggs", "ham"]}, self.project.package_data)
        
    def test_should_add_two_filenames_to_list_of_included_files_for_two_different_packages (self):
        self.project.include_file("spam", "eggs")
        self.project.include_file("monty", "ham")
        
        self.assertEquals({"monty": ["ham"], "spam": ["eggs"]}, self.project.package_data)

    def test_should_add_two_filenames_to_list_of_included_files_and_to_manifest (self):
        self.project.include_file("spam", "eggs")
        self.project.include_file("monty", "ham")
        
        self.assertEquals({"monty": ["ham"], "spam": ["eggs"]}, self.project.package_data)
        self.assertEquals(["spam/eggs", "monty/ham"], self.project.manifest_included_files)


class ProjectDataFilesTests (unittest.TestCase):
    def setUp (self):
        self.project = Project(basedir="/imaginary", name="Unittest")
     
    def test_should_return_empty_list_for_property_files_to_install (self):
        self.assertEquals([], self.project.files_to_install)
        
    def test_should_return_file_to_install (self):
        self.project.install_file("destination", "filename")
        
        self.assertEquals([("destination", ["filename"])], self.project.files_to_install)
        
    def test_should_raise_exception_when_no_destination_given (self):
        self.assertRaises(ValueError, self.project.install_file, None, "Hello world.")
    
    def test_should_raise_exception_when_no_filename_given (self):
        self.assertRaises(ValueError, self.project.install_file, "destination", None)
    
    def test_should_raise_exception_when_filename_empty (self):
        self.assertRaises(ValueError, self.project.install_file, "destination", "\t   \n")
    
    def test_should_return_files_to_install_into_same_destination (self):
        self.project.install_file("destination", "filename1")
        self.project.install_file("destination", "filename2")
        
        self.assertEquals([("destination", ["filename1", "filename2"])], self.project.files_to_install)
    
    def test_should_return_files_to_install_into_different_destinations (self):
        self.project.install_file("destination_a", "filename_a_1")
        self.project.install_file("destination_a", "filename_a_2")
        self.project.install_file("destination_b", "filename_b")
        
        self.assertEquals([("destination_a", ["filename_a_1", "filename_a_2"]),
                           ("destination_b", ["filename_b"])], self.project.files_to_install)
    
    def test_should_return_files_to_install_into_different_destinations_and_add_them_to_manifest (self):
        self.project.install_file("destination_a", "somepackage1/filename1")
        self.project.install_file("destination_a", "somepackage2/filename2")
        self.project.install_file("destination_b", "somepackage3/filename3")
        
        self.assertEquals([("destination_a", ["somepackage1/filename1", "somepackage2/filename2"]),
                           ("destination_b", ["somepackage3/filename3"])], self.project.files_to_install)
        self.assertEquals(["somepackage1/filename1", "somepackage2/filename2", "somepackage3/filename3"], self.project.manifest_included_files)
        
class LoggerTest (unittest.TestCase):
    class LoggerMock (Logger):
        def __init__ (self, threshold):
            super(LoggerTest.LoggerMock, self).__init__(threshold)
            self._logged = []
            
        def _do_log (self, level, message, *arguments):
            self._logged.append((level, message, arguments))
            
        def assert_not_logged (self, level, message, *arguments):
            if (level, message, arguments) in self._logged:
                raise AssertionError("Logged %s %s %s" % (level, message, arguments))
        
        def assert_logged (self, level, message, *arguments):
            if (level, message, arguments) not in self._logged:
                raise AssertionError("Not logged %s %s %s" % (level, message, arguments))
            
    def test_should_log_debug_message_without_arguments (self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.debug("message")
        logger.assert_logged(Logger.DEBUG, "message")

    def test_should_log_debug_message_without_arguments_but_percent_sign (self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.debug("message with %s")
        logger.assert_logged(Logger.DEBUG, "message with %s")
    
    def test_should_log_debug_message (self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.debug("message", "argument one", "argument two")
        logger.assert_logged(Logger.DEBUG, "message", "argument one", "argument two")

    def test_should_log_info_message (self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.info("message", "argument one", "argument two")
        logger.assert_logged(Logger.INFO, "message", "argument one", "argument two")
        
    def test_should_log_warn_message (self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.warn("message", "argument one", "argument two")
        logger.assert_logged(Logger.WARN, "message", "argument one", "argument two")
        
    def test_should_log_error_message (self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.error("message", "argument one", "argument two")
        logger.assert_logged(Logger.ERROR, "message", "argument one", "argument two")

    def test_should_not_not_log_info_message_when_threshold_is_set_to_warn (self):
        logger = LoggerTest.LoggerMock(Logger.WARN)
        logger.info("message", "argument one", "argument two")
        logger.assert_not_logged(Logger.INFO, "message", "argument one", "argument two")        
