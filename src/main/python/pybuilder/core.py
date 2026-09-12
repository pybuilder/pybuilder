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
    The PyBuilder core module.
    Contains the most important classes and syntax used in a
    build.py project descriptor.
"""
import fnmatch
import os
import string
from os.path import isdir, isfile, basename, relpath, sep

import itertools
import logging
import re
import sys
from datetime import datetime

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc

# Plugin install_dependencies_plugin can reload pip_common and pip_utils. Do not use from ... import ...
from pybuilder.errors import MissingPropertyException, UnspecifiedPluginNameException
from pybuilder.utils import as_list, np, ap, jp
from pybuilder.python_utils import OrderedDict

PATH_SEP_RE = re.compile(r"[/\\]")

INITIALIZER_ATTRIBUTE = "_pybuilder_initializer"
FINALIZER_ATTRIBUTE = "_pybuilder_finalizer"

ENVIRONMENTS_ATTRIBUTE = "_pybuilder_environments"

NAME_ATTRIBUTE = "_pybuilder_name"
ACTION_ATTRIBUTE = "_pybuilder_action"
ONLY_ONCE_ATTRIBUTE = "_pybuilder_action_only_once"
TEARDOWN_ATTRIBUTE = "_pybuilder_action_teardown"
BEFORE_ATTRIBUTE = "_pybuilder_before"
AFTER_ATTRIBUTE = "_pybuilder_after"

TASK_ATTRIBUTE = "_pybuilder_task"
DEPENDS_ATTRIBUTE = "_pybuilder_depends"
DEPENDENTS_ATTRIBUTE = "_pybuilder_dependents"

DESCRIPTION_ATTRIBUTE = "_pybuilder_description"


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

    def do_decoration(callable_):
        setattr(callable_, INITIALIZER_ATTRIBUTE, True)

        if "environments" in additional_arguments:
            setattr(callable_, ENVIRONMENTS_ATTRIBUTE, as_list(additional_arguments["environments"]))

        return callable_

    if possible_callable:
        return do_decoration(possible_callable[0])

    return do_decoration


def finalize(*possible_callable, **additional_arguments):
    """
    Decorator for functions that wish to perform finalization steps.
    The decorated functions are called "finalizers".

    Finalizers are executed after all tasks have been executed, at the very end of the

    Finalizers may take an additional named argument "environments" which should contain a string or list of strings
    naming the environments this finalizer applies for.

    Examples:

    @finalize
    def some_finalizer(): pass

    @finalize()
    def some_finalizer(): pass

    @finalize(environments="spam")
    def some_finalizer(): pass

    @finalize(environments=["spam", "eggs"])
    def some_finalizer(): pass
    """

    def do_decoration(callable_):
        setattr(callable_, FINALIZER_ATTRIBUTE, True)

        if "environments" in additional_arguments:
            setattr(callable_, ENVIRONMENTS_ATTRIBUTE, as_list(additional_arguments["environments"]))

        return callable_

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
        def set_name_and_task_attribute(callable_):
            setattr(callable_, TASK_ATTRIBUTE, True)
            setattr(callable_, NAME_ATTRIBUTE, callable_or_string)
            if description:
                setattr(callable_, DESCRIPTION_ATTRIBUTE, description)
            return callable_

        return set_name_and_task_attribute
    else:
        if not description:
            if callable_or_string is not None:
                setattr(callable_or_string, TASK_ATTRIBUTE, True)
                setattr(callable_or_string, NAME_ATTRIBUTE, callable_or_string.__name__)
                return callable_or_string
            else:
                def set_task_and_description_attribute(callable_):
                    setattr(callable_, TASK_ATTRIBUTE, True)
                    setattr(callable_, NAME_ATTRIBUTE, callable_.__name__)
                    return callable_

                return set_task_and_description_attribute
        else:
            def set_task_and_description_attribute(callable_):
                setattr(callable_, TASK_ATTRIBUTE, True)
                setattr(callable_, NAME_ATTRIBUTE, callable_.__name__)
                setattr(callable_, DESCRIPTION_ATTRIBUTE, description)
                return callable_

            return set_task_and_description_attribute


class description(object):
    def __init__(self, description):
        self._description = description

    def __call__(self, callable_):
        setattr(callable_, DESCRIPTION_ATTRIBUTE, self._description)
        return callable_


class depends(object):
    def __init__(self, *depends):
        self._depends = depends

    def __call__(self, callable_):
        setattr(callable_, DEPENDS_ATTRIBUTE, self._depends)
        return callable_


class dependents(object):
    def __init__(self, *dependents):
        self._dependents = dependents

    def __call__(self, callable_):
        setattr(callable_, DEPENDENTS_ATTRIBUTE, self._dependents)
        return callable_


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

    def __call__(self, callable_):
        setattr(callable_, ACTION_ATTRIBUTE, True)
        setattr(callable_, self.attribute, self.tasks)
        if self.only_once:
            setattr(callable_, ONLY_ONCE_ATTRIBUTE, True)
        if self.teardown:
            setattr(callable_, TEARDOWN_ATTRIBUTE, True)
        return callable_


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

    def __init__(self, name, version=None, url=None, declaration_only=False, eager_update=None,
                 extra=None, markers=None):
        from pybuilder import pip_common
        if version:
            try:
                version = ">=" + str(pip_common.Version(version))
                self.version_not_a_spec = True
            except pip_common.InvalidVersion:
                try:
                    version = str(pip_common.SpecifierSet(version))
                except pip_common.InvalidSpecifier:
                    raise ValueError("'%s' must be either PEP 0440 version or a version specifier set" % version)

        extras = None
        try:
            req = pip_common.Requirement(name)
            name = req.name
            extras = list(req.extras) if req.extras else None
            version = version or str(req.specifier) or None
            url = url or req.url
            markers = markers or (str(req.marker) if req.marker else None)
        except pip_common.InvalidRequirement:
            pass

        self.name = name
        self.extras = extras
        self.version = version
        self.url = url
        self.declaration_only = declaration_only
        self.eager_update = eager_update
        self.extra = pip_common.safe_extra(extra) if extra is not None else None
        self.markers = markers
        # Markers participate in identity, so that the same distribution may be declared more than
        # once under mutually exclusive conditions. Compared in canonical form so that expressions
        # differing only in quoting or whitespace are one declaration rather than two.
        self.markers_key = pip_common.normalize_markers(markers)

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return False
        return (self.name == other.name and self.version == other.version
                and self.url == other.url and self.extra == other.extra
                and self.markers_key == other.markers_key)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return (13 * hash(self.name) + 17 * hash(self.version) + 19 * hash(self.extra)
                + 23 * hash(self.markers_key))

    def __lt__(self, other):
        if not isinstance(other, Dependency):
            return True
        return self._sort_key() < other._sort_key()

    def _sort_key(self):
        # A name alone is no longer a unique key, so everything that participates in identity
        # participates in ordering too, keeping generated output stable across builds.
        return (self.name, self.version or "", self.extra or "", self.markers_key or "")

    def __str__(self):
        return self.name

    def __unicode__(self):
        return str(self)

    def __repr__(self):
        return (self.name +
                (("," + self.version) if self.version else "") +
                (("," + self.url) if self.url else "") +
                (" (declaration only)" if self.declaration_only else ""))


class RequirementsFile(object):
    """
    Represents all dependencies in a requirements file (requirements.txt).
    """

    def __init__(self, filename, declaration_only=False):
        self.name = filename
        self.version = None
        self.declaration_only = declaration_only

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

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class PluginDef:
    PYPI_PLUGIN_PROTOCOL = "pypi:"
    VCS_PLUGIN_PROTOCOL = "vcs:"

    def __init__(self, name, version=None, plugin_module_name=None):
        pip_package = pip_package_version = pip_package_url = None

        if name.startswith(PluginDef.PYPI_PLUGIN_PROTOCOL):
            pip_package = name.replace(PluginDef.PYPI_PLUGIN_PROTOCOL, "")
            if version:
                pip_package_version = str(version)
            plugin_module_name = plugin_module_name or pip_package
        elif name.startswith(PluginDef.VCS_PLUGIN_PROTOCOL):
            pip_package_url = name.replace(PluginDef.VCS_PLUGIN_PROTOCOL, "")
            if not plugin_module_name:
                raise UnspecifiedPluginNameException(name)
            pip_package = pip_package_url

        self._dep = None
        if pip_package or pip_package_version or pip_package_url:
            self._dep = Dependency(pip_package, pip_package_version, pip_package_url)
        self._val = (name, version, plugin_module_name)

    @property
    def name(self):
        return self._val[0]

    @property
    def version(self):
        return self._val[1]

    @property
    def plugin_module_name(self):
        return self._val[2]

    @property
    def dependency(self):
        return self._dep

    def __repr__(self):
        return "PluginDef [name=%r, version=%r, plugin_module_name=%r]" % (self.name,
                                                                           self.version,
                                                                           self.plugin_module_name)

    def __str__(self):
        return "%s%s%s" % (self.name, " version %s" % self.version if self.version else "",
                           ", module name '%s'" % self.plugin_module_name if self.plugin_module_name else "")

    def __eq__(self, other):
        return isinstance(other, PluginDef) and other._val == self._val

    def __hash__(self):
        return self._val.__hash__()


def _applicable_dependencies(dependencies, marker_env):
    """Dependencies whose environment markers hold in the given marker environment.

    A dependency belonging to an extras group is evaluated with the PEP 508 `extra` variable bound
    to that group, which is what makes `extra == "security"` markers resolvable.
    """
    from pybuilder import pip_common

    return [dependency for dependency in dependencies
            if pip_common.markers_apply(getattr(dependency, "markers", None), marker_env,
                                        getattr(dependency, "extra", None))]


def _duplicated_dependency_names(dependencies, marker_env):
    """Names declared more than once in a way that no environment can satisfy: either more than one
    declaration applies here, or two declarations carry the same condition and so can never be told
    apart. Declarations with mutually exclusive markers are legitimate and are not reported.
    """
    from pybuilder import pip_common

    dependencies_by_name = OrderedDict()
    for dependency in dependencies:
        dependencies_by_name.setdefault(pip_common.canonicalize_name(dependency.name), []).append(dependency)

    result = []
    for candidates in dependencies_by_name.values():
        if len(candidates) < 2:
            continue
        markers_keys = [getattr(dependency, "markers_key", None) for dependency in candidates]
        if (len(_applicable_dependencies(candidates, marker_env)) > 1
                or len(set(markers_keys)) < len(markers_keys)):
            result.append(candidates[0].name)

    return result


def _dependency_origin(dependency, capitalized=False):
    extra = getattr(dependency, "extra", None)
    origin = "runtime dependency" if extra is None else "extra '%s' dependency" % extra
    return origin[0].upper() + origin[1:] if capitalized else origin


def _dependency_spec(dependency):
    return "%s%s" % (dependency.name, dependency.version or "")


def _conflicting_dependency_messages(dependencies, marker_env):
    """Report same-name dependencies drawn from different buckets - the base requirements and the
    selected extras groups - whose specifiers cannot both be satisfied in this environment.

    Duplicates within one bucket are a declaration error reported separately; across buckets only a
    provable conflict is an error, so that an extra may legitimately tighten a base requirement.
    """
    from pybuilder import pip_common

    dependencies_by_name = OrderedDict()
    for dependency in _applicable_dependencies(dependencies, marker_env):
        if not isinstance(dependency, Dependency):
            continue
        dependencies_by_name.setdefault(pip_common.canonicalize_name(dependency.name), []).append(dependency)

    result = []
    for candidates in dependencies_by_name.values():
        if len(candidates) < 2:
            continue
        candidates = sorted(candidates)
        for index, left in enumerate(candidates):
            for right in candidates[index + 1:]:
                if left.extra == right.extra:
                    continue
                if pip_common.specifiers_conflict(left.version, right.version):
                    result.append("%s '%s' conflicts with %s '%s' in this environment." %
                                  (_dependency_origin(left, capitalized=True), _dependency_spec(left),
                                   _dependency_origin(right), _dependency_spec(right)))

    return result


class Project(object):
    """
    Descriptor for a project to be built. A project has a number of attributes
    as well as some convenience methods to access these properties.
    """

    def __init__(self, basedir, version="1.0.dev0", name=None, offline=False, no_venvs=False):
        self.name = name
        self._version = None
        self._dist_version = None
        self.offline = offline
        self.no_venvs = no_venvs
        self.version = version
        self.basedir = ap(basedir)
        if not self.name:
            self.name = basename(basedir)

        self.default_task = None

        self.summary = ""
        self.description = ""

        self.author = ""
        self.authors = []
        self.maintainer = ""
        self.maintainers = []

        self.license = ""
        self.url = ""
        self.urls = {}

        self._requires_python = ""
        self._obsoletes = []
        self._explicit_namespaces = []
        self._properties = {"verbose": False}
        self._install_dependencies = set()
        self._build_dependencies = set()
        self._plugin_dependencies = set()
        self._manifest_included_files = []
        self._manifest_included_directories = []
        self._package_data = OrderedDict()
        self._files_to_install = []
        self._preinstall_script = None
        self._postinstall_script = None
        self._environments = ()

    def __str__(self):
        return "[Project name=%s basedir=%s]" % (self.name, self.basedir)

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        self._version = value
        if value.endswith('.dev'):
            value += datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        self._dist_version = value

    @property
    def requires_python(self):
        return self._requires_python

    @requires_python.setter
    def requires_python(self, value):
        from pybuilder import pip_common
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
        from pybuilder import pip_common

        # Validation runs before any target venv exists, so markers are evaluated against the
        # interpreter running the build - which is the interpreter every venv is created from.
        marker_env = pip_common.default_environment()
        extras = self.extras_dependencies
        result = []

        for name in _duplicated_dependency_names(self.build_dependencies, marker_env):
            result.append("Build dependency '%s' has been defined multiple times." % name)

        for name in _duplicated_dependency_names(self.base_dependencies, marker_env):
            result.append("Runtime dependency '%s' has been defined multiple times." % name)

        live_build_dependencies = {pip_common.canonicalize_name(d.name): d
                                   for d in _applicable_dependencies(self.build_dependencies, marker_env)}
        for dependency in _applicable_dependencies(self.dependencies, marker_env):
            if pip_common.canonicalize_name(dependency.name) in live_build_dependencies:
                result.append("Runtime dependency '%s' has also been given as build dependency." % dependency.name)

        for extra_name, extra_dependencies in extras.items():
            for name in _duplicated_dependency_names(extra_dependencies, marker_env):
                result.append("Extra '%s' dependency '%s' has been defined multiple times." % (extra_name, name))

        result.extend(_conflicting_dependency_messages(self.dependencies, marker_env))

        for extra_name in self.selected_extras:
            if extra_name not in extras:
                declared = sorted(extras.keys())
                result.append("Extra '%s' selected by 'install_dependencies_extras' is not declared by this "
                              "project. %s" % (extra_name,
                                               ("Declared extras are: %s." % ", ".join(declared)) if declared
                                               else "This project declares no extras."))

        return result

    @property
    def properties(self):
        result = self._properties
        result["basedir"] = self.basedir
        return result

    @property
    def base_dependencies(self):
        """Runtime dependencies declared without an extras group.

        This is what is published as the distribution's mandatory requirements; a build-time
        decision to install an extra must never reach it.
        """
        return list(sorted(d for d in self._install_dependencies if getattr(d, 'extra', None) is None))

    @property
    def selected_extras(self):
        """Normalized names of the extras groups selected by the `install_dependencies_extras`
        property. Unknown names are retained here and reported by `validate`.
        """
        from pybuilder import pip_common

        selection = self.get_property("install_dependencies_extras")
        if not selection:
            return []

        selection = as_list(selection)
        if "*" in selection:
            return list(self.extras_dependencies.keys())

        return [pip_common.safe_extra(extra_name) for extra_name in selection]

    @property
    def dependencies(self):
        """Runtime dependencies to install: the base ones plus every selected extras group."""
        selected = self.selected_extras
        if not selected:
            return self.base_dependencies

        extras = self.extras_dependencies
        result = self.base_dependencies
        for extra_name in selected:
            result.extend(extras.get(extra_name, ()))
        return list(sorted(result))

    @property
    def build_dependencies(self):
        return list(sorted(self._build_dependencies))

    @property
    def plugin_dependencies(self):
        return list(sorted(self._plugin_dependencies))

    def depends_on(self, name, version=None, url=None, declaration_only=False, eager_update=None,
                   extra=None, markers=None):
        self._install_dependencies.add(Dependency(name, version, url, declaration_only,
                                                  eager_update=eager_update, extra=extra, markers=markers))

    def build_depends_on(self, name, version=None, url=None, declaration_only=False, eager_update=None, markers=None):
        self._build_dependencies.add(Dependency(name, version, url, declaration_only,
                                                eager_update=eager_update, markers=markers))

    def depends_on_requirements(self, file, declaration_only=False):
        self._install_dependencies.add(RequirementsFile(file, declaration_only=declaration_only))

    def build_depends_on_requirements(self, file):
        self._build_dependencies.add(RequirementsFile(file))

    def plugin_depends_on(self, name, version=None, url=None, declaration_only=False, eager_update=None, markers=None):
        self._plugin_dependencies.add(Dependency(name, version, url, declaration_only,
                                                 eager_update=eager_update, markers=markers))

    @property
    def extras_dependencies(self):
        result = OrderedDict()
        for dep in sorted(self._install_dependencies):
            extra = getattr(dep, 'extra', None)
            if extra is not None:
                result.setdefault(extra, []).append(dep)
        return result

    @property
    def environments(self):
        return self._environments

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
        package_name = package_name or ""

        if not filename or filename.strip() == "":
            raise ValueError("Missing argument filename.")

        full_filename = np(jp(package_name.replace(".", sep), filename))
        self._manifest_include(full_filename)

        self._add_package_data(package_name, filename)

    def include_directory(self, package_path, patterns_list, package_root=""):
        if not package_path or package_path.strip() == "":
            raise ValueError("Missing argument package_path.")

        if not patterns_list:
            raise ValueError("Missing argument patterns_list.")
        patterns_list = as_list(patterns_list)

        package_name = PATH_SEP_RE.sub(".", package_path)
        self._manifest_include_directory(package_path, patterns_list)

        package_full_path = self.expand_path(package_root, package_path)

        for root, dirnames, filenames in os.walk(package_full_path):
            filenames = list(fnmatch.filter(filenames, pattern) for pattern in patterns_list)

            for filename in itertools.chain.from_iterable(filenames):
                full_path = np(jp(root, filename))
                relative_path = relpath(full_path, package_full_path)
                self._add_package_data(package_name, relative_path)

    def _add_package_data(self, package_name, filename):
        filename = filename.replace("\\", "/")
        self._package_data.setdefault(package_name, []).append(filename)

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
        return np(jp(*elements))

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


class Logger(logging.Handler):
    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10

    def __init__(self, level=INFO, log_time_format=None):
        super(Logger, self).__init__(level)
        self.log_time_format = log_time_format

    def emit(self, record):
        self._do_log(record.levelno, record.getMessage())

    def _do_log(self, level, message, *arguments):
        pass

    @staticmethod
    def _format_message(message, *arguments):
        if arguments:
            return message % arguments
        return message

    def log(self, level, message, *arguments):
        if level >= self.level:
            self._do_log(level, message, *arguments)

    def debug(self, message, *arguments):
        self.log(Logger.DEBUG, message, *arguments)

    def info(self, message, *arguments):
        self.log(Logger.INFO, message, *arguments)

    def warn(self, message, *arguments):
        self.log(Logger.WARN, message, *arguments)

    def error(self, message, *arguments):
        self.log(Logger.ERROR, message, *arguments)
