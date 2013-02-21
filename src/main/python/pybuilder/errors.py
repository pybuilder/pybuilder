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
class PythonbuilderException (Exception):
    def __init__(self, message, *arguments):
        self._message = message
        self._arguments = arguments
    
    @property
    def message (self):
        return self._message % self._arguments

    def __str__ (self):
        return self.message

class InvalidNameException (PythonbuilderException):
    def __init__ (self, name):
        super(InvalidNameException, self).__init__("Invalid name: %s", name)

class NoSuchTaskException (PythonbuilderException):
    def __init__(self, name):
        super(NoSuchTaskException, self).__init__("No such task %s", name)

class CircularTaskDependencyException (PythonbuilderException):
    def __init__(self, first, second=None):
        if second:
            super(CircularTaskDependencyException, self).__init__("Circular task dependency detected between %s and %s", first, second)
        self.first = first
        self.second = second
        
class MissingPrerequisiteException (PythonbuilderException):
    def __init__ (self, prerequisite, caller="n/a"):
        super(MissingPrerequisiteException, self).__init__("Missing prerequisite %s required by %s", 
                                                           prerequisite, caller)

class MissingTaskDependencyException (PythonbuilderException):
    def __init__(self, source, dependency):
        super(MissingTaskDependencyException, self).__init__("Missing task '%s' required for task '%s'", 
                                                             dependency, source)    

class MissingActionDependencyException (PythonbuilderException):
    def __init__(self, source, dependency):
        super(MissingActionDependencyException, self).__init__("Missing task '%s' required for action '%s'", 
                                                               dependency, source)    

class MissingPluginException (PythonbuilderException):
    def __init__(self, plugin, message=""):
        super(MissingPluginException, self).__init__("Missing plugin '%s': %s", plugin, message)
                    
class BuildFailedException (PythonbuilderException):
    pass

class MissingPropertyException (PythonbuilderException):
    def __init__ (self, property):
        super(MissingPropertyException, self).__init__("No such property: %s", property)

class ProjectValidationFailedException (BuildFailedException):
    def __init__ (self, validation_messages):
        BuildFailedException.__init__(self, "Project validation failed: " + "\n-".join(validation_messages))
        self.validation_messages = validation_messages

class InternalException (PythonbuilderException):
    pass