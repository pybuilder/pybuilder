#   -*- coding: utf-8 -*-
#
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

"""
    The PyBuilder error module.
    Defines all possible errors that can arise during the execution of PyBuilder.
"""


class PyBuilderException(Exception):

    def __init__(self, message, *arguments):
        self._message = message
        self._arguments = arguments

    @property
    def message(self):
        return self._message % self._arguments

    def __str__(self):
        return self.message


class InvalidNameException(PyBuilderException):

    def __init__(self, name):
        super(InvalidNameException, self).__init__("Invalid name: %s", name)


class NoSuchTaskException(PyBuilderException):

    def __init__(self, name):
        super(NoSuchTaskException, self).__init__("No such task %s", name)


class CircularTaskDependencyException(PyBuilderException):

    def __init__(self, first, second=None):
        if second:
            super(
                CircularTaskDependencyException, self).__init__("Circular task dependency detected between %s and %s",
                                                                first,
                                                                second)
        self.first = first
        self.second = second


class MissingPrerequisiteException(PyBuilderException):

    def __init__(self, prerequisite, caller="n/a"):
        super(
            MissingPrerequisiteException, self).__init__("Missing prerequisite %s required by %s",
                                                         prerequisite, caller)


class MissingTaskDependencyException(PyBuilderException):

    def __init__(self, source, dependency):
        super(
            MissingTaskDependencyException, self).__init__("Missing task '%s' required for task '%s'",
                                                           dependency, source)


class MissingActionDependencyException(PyBuilderException):

    def __init__(self, source, dependency):
        super(
            MissingActionDependencyException, self).__init__("Missing task '%s' required for action '%s'",
                                                             dependency, source)


class MissingPluginException(PyBuilderException):

    def __init__(self, plugin, message=""):
        super(MissingPluginException, self).__init__(
            "Missing plugin '%s': %s", plugin, message)


class BuildFailedException(PyBuilderException):
    pass


class MissingPropertyException(PyBuilderException):

    def __init__(self, property):
        super(MissingPropertyException, self).__init__(
            "No such property: %s", property)


class ProjectValidationFailedException(BuildFailedException):

    def __init__(self, validation_messages):
        BuildFailedException.__init__(
            self, "Project validation failed: " + "\n-".join(validation_messages))
        self.validation_messages = validation_messages


class InternalException(PyBuilderException):
    pass


class DependenciesNotResolvedException(InternalException):
    def __init__(self):
        super(DependenciesNotResolvedException, self).__init__("Dependencies have not been resolved.")
