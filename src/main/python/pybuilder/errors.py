#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2020 PyBuilder Team
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

from pprint import pformat


class PyBuilderException(Exception):
    def __init__(self, message, *arguments):
        super(PyBuilderException, self).__init__(message, *arguments)
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
    def __init__(self, message, *args):
        if isinstance(message, (list, tuple)):
            cycles = message
            super(CircularTaskDependencyException, self).__init__("Circular task dependencies detected:\n%s",
                                                                  "\n".join("\t" + pformat(cycle) for cycle in cycles)
                                                                  )
        else:
            super(CircularTaskDependencyException, self).__init__(message,
                                                                  *args)


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


class RequiredTaskExclusionException(PyBuilderException):
    def __init__(self, source, dependency):
        super(
            RequiredTaskExclusionException, self).__init__("Task '%s' is required for task '%s' and cannot be excluded",
                                                           dependency, source)


class MissingActionDependencyException(PyBuilderException):
    def __init__(self, source, dependency):
        super(
            MissingActionDependencyException, self).__init__("Missing task '%s' required for action '%s'",
                                                             dependency, source)


class MissingPluginException(PyBuilderException):
    def __init__(self, plugin, message=""):
        super(MissingPluginException, self).__init__(
            "Missing plugin %s: %s", plugin, message)


class UnspecifiedPluginNameException(PyBuilderException):
    def __init__(self, plugin):
        super(UnspecifiedPluginNameException, self).__init__(
            "Plugin module name is not specified '%s'", plugin)


class IncompatiblePluginException(PyBuilderException):
    def __init__(self, plugin_name, required_pyb_version, actual_pyb_version):
        super(IncompatiblePluginException, self).__init__(
            "Plugin '%s': required PyB version '%s' does not match current '%s'", plugin_name, required_pyb_version,
            actual_pyb_version)


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
