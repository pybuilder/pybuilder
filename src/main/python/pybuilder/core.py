#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2015 PyBuilder Team
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
    The PyBuilder core module.
    Contains the most important classes and syntax used in a
    build.py project descriptor.
"""

import fnmatch
import itertools
import os
import re
import string
import sys
from datetime import datetime
from os.path import sep as PATH_SEPARATOR, normcase as nc, join as jp, isdir, isfile, basename

# Plugin install_dependencies_plugin can reload pip_common and pip_utils. Do not use from ... import ...
from pybuilder import pip_common
from pybuilder.errors import MissingPropertyException
from pybuilder.utils import as_list

PATH_SEP_RE = re.compile("[\\/]")

INITIALIZER_ATTRIBUTE = "_python_builder_initializer"

ENVIRONMENTS_ATTRIBUTE = "_python_builder_environments"

NAME_ATTRIBUTE = "_python_builder_name"
ACTION_ATTRIBUTE = "_python_builder_action"
ONLY_ONCE_ATTRIBUTE = "_python_builder_action_only_once"
TEARDOWN_ATTRIBUTE = "_python_builder_action_teardown"
BEFORE_ATTRIBUTE = "_python_builder_before"
AFTER_ATTRIBUTE = "_python_builder_after"

TASK_ATTRIBUTE = "_python_builder_task"
DEPENDS_ATTRIBUTE = "_python_builder_depends"
DEPENDENTS_ATTRIBUTE = "_python_builder_dependents"

DESCRIPTION_ATTRIBUTE = "_python_builder_description"


def init(*possible_callable, **additional_arguments):
    """
    Decorator for functions that wish to perform initialization steps.
    The decorated functions are called "initializers".

    Initializers are executed after all plugins and projects have been loaded
    but before any task is executed.

    Initializers may take an additional named argument "environments" which should contain a string or list of strings
    naming the environments this initializer applies for.

    Examples:

    @init
    def some_initializer(): pass

    @init()
    def some_initializer(): pass

    @init(environments="spam")
    def some_initializer(): pass

    @init(environments=["spam", "eggs"])
    def some_initializer(): pass
    """

    def do_decoration(callable):
        setattr(callable, INITIALIZER_ATTRIBUTE, True)

        if "environments" in additional_arguments:
            setattr(callable, ENVIRONMENTS_ATTRIBUTE, as_list(additional_arguments["environments"]))

        return callable

    if possible_callable:
        return do_decoration(possible_callable[0])

    return do_decoration


def task(callable_or_string=None, description=None):
    """
    Decorator for functions that should be used as tasks. Tasks are the main
    building blocks of projects.
    You can use this decorator either plain (no argument) or with
    a string argument, which overrides the default name.
    """
    if isinstance(callable_or_string, str):
        def set_name_and_task_attribute(callable):
            setattr(callable, TASK_ATTRIBUTE, True)
            setattr(callable, NAME_ATTRIBUTE, callable_or_string)
            if description:
                setattr(callable, DESCRIPTION_ATTRIBUTE, description)
            return callable

        return set_name_and_task_attribute
    else:
        if not description:
            if callable_or_string is not None:
                setattr(callable_or_string, TASK_ATTRIBUTE, True)
                setattr(callable_or_string, NAME_ATTRIBUTE, callable_or_string.__name__)
                return callable_or_string
            else:
                def set_task_and_description_attribute(callable):
                    setattr(callable, TASK_ATTRIBUTE, True)
                    setattr(callable, NAME_ATTRIBUTE, callable.__name__)
                    return callable

                return set_task_and_description_attribute
        else:
            def set_task_and_description_attribute(callable):
                setattr(callable, TASK_ATTRIBUTE, True)
                setattr(callable, NAME_ATTRIBUTE, callable.__name__)
                setattr(callable, DESCRIPTION_ATTRIBUTE, description)
                return callable

            return set_task_and_description_attribute


class description(object):
    def __init__(self, description):
        self._description = description

    def __call__(self, callable):
        setattr(callable, DESCRIPTION_ATTRIBUTE, self._description)
        return callable


class depends(object):
    def __init__(self, *depends):
        self._depends = depends

    def __call__(self, callable):
        setattr(callable, DEPENDS_ATTRIBUTE, self._depends)
        return callable


class dependents(object):
    def __init__(self, *dependents):
        self._dependents = dependents

    def __call__(self, callable):
        setattr(callable, DEPENDENTS_ATTRIBUTE, self._dependents)
        return callable


class optional(object):
    def __init__(self, *names):
        self._names = names

    def __call__(self):
        return self._names


class BaseAction(object):
    def __init__(self, attribute, only_once, tasks, teardown=False):
        self.tasks = tasks
        self.attribute = attribute
        self.only_once = only_once
        self.teardown = teardown

    def __call__(self, callable):
        setattr(callable, ACTION_ATTRIBUTE, True)
        setattr(callable, self.attribute, self.tasks)
        if self.only_once:
            setattr(callable, ONLY_ONCE_ATTRIBUTE, True)
        if self.teardown:
            setattr(callable, TEARDOWN_ATTRIBUTE, True)
        return callable


class before(BaseAction):
    def __init__(self, tasks, only_once=False):
        super(before, self).__init__(BEFORE_ATTRIBUTE, only_once, tasks)


class after(BaseAction):
    def __init__(self, tasks, only_once=False, teardown=False):
        super(after, self).__init__(AFTER_ATTRIBUTE, only_once, tasks, teardown)


def use_bldsup(build_support_dir="bldsup"):
    """Specify a local build support directory for build specific extensions.

    use_plugin(name) and import will look for python modules in BUILD_SUPPORT_DIR.

    WARNING: The BUILD_SUPPORT_DIR must exist and must have an __init__.py file in it.
    """
    assert isdir(build_support_dir), "use_bldsup('{0}'): The {0} directory must exist!".format(
        build_support_dir)
    init_file = jp(build_support_dir, "__init__.py")
    assert isfile(init_file), "use_bldsup('{0}'): The {1} file must exist!".format(build_support_dir, init_file)
    sys.path.insert(0, build_support_dir)


def use_plugin(name, version=None, plugin_module_name=None):
    from pybuilder.reactor import Reactor
    reactor = Reactor.current_instance()
    if reactor is not None:
        reactor.require_plugin(name, version, plugin_module_name)


class Author(object):
    def __init__(self, name, email=None, roles=None):
        self.name = name
        self.email = email
        self.roles = roles or []


class Dependency(object):
    """
    Defines a dependency to another module. Use the
        depends_on
    method from class Project to add a dependency to a project.
    """

    def __init__(self, name, version=None, url=None):
        self.name = name

        if version:
            try:
                version = ">=" + str(pip_common.Version(version))
                self.version_not_a_spec = True
            except pip_common.InvalidVersion:
                try:
                    version = str(pip_common.SpecifierSet(version))
                except pip_common.InvalidSpecifier:
                    raise ValueError("'%s' must be either PEP 0440 version or a version specifier set" % version)

        self.version = version
        self.url = url

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return False
        return self.name == other.name and self.version == other.version and self.url == other.url

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return 13 * hash(self.name) + 17 * hash(self.version)

    def __lt__(self, other):
        if not isinstance(other, Dependency):
            return True
        return self.name < other.name

    def __str__(self):
        return self.name

    def __unicode__(self):
        return str(self)

    def __repr__(self):
        return self.name + ("," + self.version if self.version else "") + ("," + self.url if self.url else "")


class RequirementsFile(object):
    """
    Represents all dependencies in a requirements file (requirements.txt).
    """

    def __init__(self, filename):
        self.name = filename
        self.version = None

    def __eq__(self, other):
        if not isinstance(other, RequirementsFile):
            return False
        return self.name == other.name

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        if not isinstance(other, RequirementsFile):
            return False
        return self.name < other.name

    def __hash__(self):
        return 42 * hash(self.name)


class Project(object):
    """
    Descriptor for a project to be built. A project has a number of attributes
    as well as some convenience methods to access these properties.
    """

    def __init__(self, basedir, version="1.0.dev0", name=None):
        self.name = name
        self._version = None
        self._dist_version = None
        self.version = version
        self.basedir = basedir
        if not self.name:
            self.name = basename(basedir)

        self.default_task = None

        self.summary = ""
        self.home_page = ""
        self.description = ""
        self.author = ""
        self.authors = []
        self.license = ""
        self.url = ""
        self._requires_python = ""
        self._obsoletes = []
        self._explicit_namespaces = []
        self._properties = {"verbose": False}
        self._install_dependencies = set()
        self._build_dependencies = set()
        self._plugin_dependencies = set()
        self._manifest_included_files = []
        self._manifest_included_directories = []
        self._package_data = {}
        self._files_to_install = []
        self._preinstall_script = None
        self._postinstall_script = None

    def __str__(self):
        return "[Project name=%s basedir=%s]" % (self.name, self.basedir)

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        self._version = value
        if value.endswith('.dev'):
            value += datetime.utcnow().strftime("%Y%m%d%H%M%S")
        self._dist_version = value

    @property
    def requires_python(self):
        return self._requires_python

    @requires_python.setter
    def requires_python(self, value):
        spec_set = pip_common.SpecifierSet(value)
        self._requires_python = str(spec_set)

    @property
    def obsoletes(self):
        return self._obsoletes

    @obsoletes.setter
    def obsoletes(self, value):
        self._obsoletes = as_list(value)

    @property
    def explicit_namespaces(self):
        return self._explicit_namespaces

    @explicit_namespaces.setter
    def explicit_namespaces(self, value):
        self._explicit_namespaces = as_list(value)

    @property
    def dist_version(self):
        return self._dist_version

    def validate(self):
        """
        Validates the project returning a list of validation error messages if the project is not valid.
        Returns an empty list if the project is valid.
        """
        result = self.validate_dependencies()

        return result

    def validate_dependencies(self):
        result = []

        build_dependencies_found = {}

        for dependency in self.build_dependencies:
            if dependency.name in build_dependencies_found:
                if build_dependencies_found[dependency.name] == 1:
                    result.append("Build dependency '%s' has been defined multiple times." % dependency.name)
                build_dependencies_found[dependency.name] += 1
            else:
                build_dependencies_found[dependency.name] = 1

        runtime_dependencies_found = {}

        for dependency in self.dependencies:
            if dependency.name in runtime_dependencies_found:
                if runtime_dependencies_found[dependency.name] == 1:
                    result.append("Runtime dependency '%s' has been defined multiple times." % dependency.name)
                runtime_dependencies_found[dependency.name] += 1
            else:
                runtime_dependencies_found[dependency.name] = 1
            if dependency.name in build_dependencies_found:
                result.append("Runtime dependency '%s' has also been given as build dependency." % dependency.name)

        return result

    @property
    def properties(self):
        result = self._properties
        result["basedir"] = self.basedir
        return result

    @property
    def dependencies(self):
        return list(sorted(self._install_dependencies))

    @property
    def build_dependencies(self):
        return list(sorted(self._build_dependencies))

    @property
    def plugin_dependencies(self):
        return list(sorted(self._plugin_dependencies))

    def depends_on(self, name, version=None, url=None):
        self._install_dependencies.add(Dependency(name, version, url))

    def build_depends_on(self, name, version=None, url=None):
        self._build_dependencies.add(Dependency(name, version, url))

    def depends_on_requirements(self, file):
        self._install_dependencies.add(RequirementsFile(file))

    def build_depends_on_requirements(self, file):
        self._build_dependencies.add(RequirementsFile(file))

    def plugin_depends_on(self, name, version=None, url=None):
        self._plugin_dependencies.add(Dependency(name, version, url))

    @property
    def setup_preinstall_script(self):
        return self._preinstall_script

    def pre_install_script(self, script):
        self._preinstall_script = script

    @property
    def setup_postinstall_script(self):
        return self._postinstall_script

    def post_install_script(self, script):
        self._postinstall_script = script

    @property
    def manifest_included_files(self):
        return self._manifest_included_files

    @property
    def manifest_included_directories(self):
        return self._manifest_included_directories

    def _manifest_include(self, glob_pattern):
        if not glob_pattern or glob_pattern.strip() == "":
            raise ValueError("Missing glob_pattern argument.")

        self._manifest_included_files.append(glob_pattern)

    def _manifest_include_directory(self, directory, patterns_list):
        if not directory or directory.strip() == "":
            raise ValueError("Missing directory argument.")

        patterns_list = map(lambda s: s.strip(), patterns_list)
        patterns_list = tuple(filter(bool, patterns_list))
        if len(patterns_list) == 0:
            raise ValueError("Missing patterns_list argument.")

        directory_to_include = (directory, patterns_list)
        self._manifest_included_directories.append(directory_to_include)

    @property
    def package_data(self):
        return self._package_data

    def include_file(self, package_name, filename):
        if not package_name or package_name.strip() == "":
            raise ValueError("Missing argument package name.")

        if not filename or filename.strip() == "":
            raise ValueError("Missing argument filename.")

        full_filename = jp(package_name, filename)
        self._manifest_include(full_filename)

        if package_name not in self._package_data:
            self._package_data[package_name] = [filename]
            return
        self._package_data[package_name].append(filename)

    def include_directory(self, package_path, patterns_list, package_root=""):
        if not package_path or package_path.strip() == "":
            raise ValueError("Missing argument package_path.")

        if not patterns_list:
            raise ValueError("Missing argument patterns_list.")

        package_name = package_path.replace(PATH_SEPARATOR, '.')
        self._manifest_include_directory(package_path, patterns_list)

        package_full_path = jp(package_root, package_path)

        for root, dirnames, filenames in os.walk(package_full_path):
            filenames = list(fnmatch.filter(filenames, pattern) for pattern in patterns_list)

            for filename in itertools.chain.from_iterable(filenames):
                full_path = jp(root, filename)
                relative_path = full_path.replace(package_full_path, '', 1).lstrip(PATH_SEPARATOR)
                self._package_data.setdefault(package_name, []).append(relative_path)

    @property
    def files_to_install(self):
        return self._files_to_install

    def install_file(self, destination, filename):
        if not destination:
            raise ValueError("Missing argument destination")

        if not filename or filename.strip() == "":
            raise ValueError("Missing argument filename")

        current_tuple = None
        for installation_tuple in self.files_to_install:
            destination_name = installation_tuple[0]

            if destination_name == destination:
                current_tuple = installation_tuple

        if current_tuple:
            list_of_files_within_tuple = current_tuple[1]
            list_of_files_within_tuple.append(filename)
        else:
            initial_tuple = (destination, [filename])
            self.files_to_install.append(initial_tuple)

        self._manifest_include(filename)

    def expand(self, format_string):
        previous = None
        result = format_string
        while previous != result:
            try:
                previous = result
                result = string.Template(result).substitute(self.properties)
            except KeyError as e:
                raise MissingPropertyException(e)
        return result

    def expand_path(self, format_string, *additional_path_elements):
        elements = [self.basedir]
        elements += list(PATH_SEP_RE.split(self.expand(format_string)))
        elements += list(additional_path_elements)
        return nc(jp(*elements))

    def get_property(self, key, default_value=None):
        return self.properties.get(key, default_value)

    def get_mandatory_property(self, key):
        if not self.has_property(key):
            raise MissingPropertyException(key)
        return self.get_property(key)

    def has_property(self, key):
        return key in self.properties

    def set_property(self, key, value):
        self.properties[key] = value

    def set_property_if_unset(self, key, value):
        if not self.has_property(key):
            self.set_property(key, value)


class Logger(object):
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4

    def __init__(self, threshold=INFO):
        self.threshold = threshold

    def _do_log(self, level, message, *arguments):
        pass

    @staticmethod
    def _format_message(message, *arguments):
        if arguments:
            return message % arguments
        return message

    def log(self, level, message, *arguments):
        if level >= self.threshold:
            self._do_log(level, message, *arguments)

    def debug(self, message, *arguments):
        self.log(Logger.DEBUG, message, *arguments)

    def info(self, message, *arguments):
        self.log(Logger.INFO, message, *arguments)

    def warn(self, message, *arguments):
        self.log(Logger.WARN, message, *arguments)

    def error(self, message, *arguments):
        self.log(Logger.ERROR, message, *arguments)
