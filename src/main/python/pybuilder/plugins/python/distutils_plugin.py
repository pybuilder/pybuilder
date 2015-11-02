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

import string
import subprocess
import sys

import os

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO


from pybuilder.core import (after,
                            before,
                            use_plugin,
                            init,
                            task,
                            RequirementsFile,
                            Dependency)
from pybuilder.errors import BuildFailedException
from pybuilder.utils import as_list, is_string, is_notstr_iterable

from .setuptools_plugin_helper import build_dependency_version_string

use_plugin("python.core")

DATA_FILES_PROPERTY = "distutils_data_files"
SETUP_TEMPLATE = string.Template("""#!/usr/bin/env python
$remove_hardlink_capabilities_for_shared_filesystems
from $module import setup

if __name__ == '__main__':
    setup(
        name = '$name',
        version = '$version',
        description = '''$summary''',
        long_description = '''$description''',
        author = "$author",
        author_email = "$author_email",
        license = '$license',
        url = '$url',
        scripts = $scripts,
        packages = $packages,
        py_modules = $modules,
        classifiers = $classifiers,
        entry_points = $console_scripts,
        data_files = $data_files,
        package_data = $package_data,
        install_requires = $dependencies,
        dependency_links = $dependency_links,
        zip_safe=True
    )
""")


def default(value, default=""):
    if value is None:
        return default
    return value


@init
def initialize_distutils_plugin(project):
    project.set_property_if_unset("distutils_commands", ["sdist", "bdist_dumb"])
    # Workaround for http://bugs.python.org/issue8876 , unable to build a bdist
    # on a filesystem that does not support hardlinks
    project.set_property_if_unset("distutils_issue8876_workaround_enabled", False)
    project.set_property_if_unset("distutils_classifiers", [
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python"
    ])
    project.set_property_if_unset("distutils_use_setuptools", True)
    project.set_property_if_unset("distutils_upload_repository", None)


@after("package")
def write_setup_script(project, logger):
    setup_script = project.expand_path("$dir_dist", "setup.py")
    logger.info("Writing setup.py as %s", setup_script)

    with open(setup_script, "w") as setup_file:
        setup_file.write(render_setup_script(project))

    os.chmod(setup_script, 0o755)


def render_setup_script(project):
    author = ", ".join(map(lambda a: a.name, project.authors))
    author_email = ", ".join(map(lambda a: a.email, project.authors))

    template_values = {
        "module": "setuptools" if project.get_property("distutils_use_setuptools") else "distutils.core",
        "name": project.name,
        "version": project.version,
        "summary": default(project.summary),
        "description": default(project.description),
        "author": author,
        "author_email": author_email,
        "license": default(project.license),
        "url": default(project.url),
        "scripts": build_scripts_string(project),
        "packages": build_packages_string(project),
        "modules": build_modules_string(project),
        "classifiers": build_classifiers_string(project),
        "console_scripts": build_console_scripts_string(project),
        "data_files": build_data_files_string(project),
        "package_data": build_package_data_string(project),
        "dependencies": build_install_dependencies_string(project),
        "dependency_links": build_dependency_links_string(project),
        "remove_hardlink_capabilities_for_shared_filesystems": (
            "import os\ndel os.link"
            if project.get_property("distutils_issue8876_workaround_enabled")
            else "")
    }

    return SETUP_TEMPLATE.substitute(template_values)


@after("package")
def write_manifest_file(project, logger):
    if len(project.manifest_included_files) == 0 and len(project.manifest_included_directories) == 0:
        logger.debug("No data to write into MANIFEST.in")
        return

    logger.debug("Files included in MANIFEST.in: %s" %
                 project.manifest_included_files)

    manifest_filename = project.expand_path("$dir_dist", "MANIFEST.in")
    logger.info("Writing MANIFEST.in as %s", manifest_filename)

    with open(manifest_filename, "w") as manifest_file:
        manifest_file.write(render_manifest_file(project))

    os.chmod(manifest_filename, 0o664)


def render_manifest_file(project):
    manifest_content = StringIO()

    for included_file in project.manifest_included_files:
        manifest_content.write("include %s\n" % included_file)

    for directory, pattern_list in project.manifest_included_directories:
        patterns = ' '.join(pattern_list)
        manifest_content.write("recursive-include %s %s\n" % (directory, patterns))

    return manifest_content.getvalue()


@before("publish")
def build_binary_distribution(project, logger):
    logger.info("Building binary distribution in %s",
                project.expand_path("$dir_dist"))

    commands = as_list(project.get_property("distutils_commands"))
    execute_distutils(project, logger, commands)


@task("install")
def install_distribution(project, logger):
    logger.info("Installing project %s-%s", project.name, project.version)

    execute_distutils(project, logger, as_list("install"))


@task("upload")
def upload(project, logger):
    repository = project.get_property("$distutils_upload_repository")
    repository_args = []
    if repository:
        repository_args = ["-r", repository]
    upload_cmd_line = []
    upload_cmd_line.extend(project.get_property("distutils_commands"))
    upload_cmd_line.append("upload")
    upload_cmd_line.extend(repository_args)

    logger.info("Uploading project %s-%s%s", project.name, project.version,
                (" to repository '%s'" % repository) if repository else "")
    execute_distutils(project, logger, [upload_cmd_line])


def execute_distutils(project, logger, distutils_commands):
    reports_dir = project.expand_path("$dir_reports", "distutils")
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)

    setup_script = project.expand_path("$dir_dist", "setup.py")

    for command in distutils_commands:
        logger.debug("Executing distutils command %s", command)
        if is_string(command):
            output_file_path = os.path.join(reports_dir, command.replace("/", ""))
        else:
            output_file_path = os.path.join(reports_dir, "__".join(command).replace("/", ""))
        with open(output_file_path, "w") as output_file:
            commands = [sys.executable, setup_script]
            if project.get_property("verbose"):
                commands.append("-v")
            if is_string(command):
                commands.extend(command.split())
            else:
                commands.extend(command)
            process = subprocess.Popen(commands,
                                       cwd=project.expand_path("$dir_dist"),
                                       stdout=output_file,
                                       stderr=output_file,
                                       shell=False)
            return_code = process.wait()
            if return_code != 0:
                raise BuildFailedException(
                    "Error while executing setup command %s, see %s for details" % (command, output_file_path))


def strip_comments(requirements):
    return [requirement for requirement in requirements
            if not requirement.strip().startswith("#")]


def quote(requirements):
    return ['"%s"' % requirement for requirement in requirements]


def is_editable_requirement(requirement):
    return "-e " in requirement or "--editable " in requirement


def flatten_and_quote(requirements_file):
    with open(requirements_file.name, 'r') as requirements_file:
        requirements = [requirement.strip("\n") for requirement in requirements_file.readlines()]
        requirements = [requirement for requirement in requirements if requirement]
        return quote(strip_comments(requirements))


def format_single_dependency(dependency):
    return '%s%s' % (dependency.name, build_dependency_version_string(dependency))


def build_install_dependencies_string(project):
    dependencies = [
        dependency for dependency in project.dependencies
        if isinstance(dependency, Dependency) and not dependency.url]
    requirements = [
        requirement for requirement in project.dependencies
        if isinstance(requirement, RequirementsFile)]
    if not dependencies and not requirements:
        return "[]"

    dependencies = [format_single_dependency(dependency) for dependency in dependencies]
    requirements = [strip_comments(flatten_and_quote(requirement)) for requirement in requirements]
    flattened_requirements = [dependency for dependency_list in requirements for dependency in dependency_list]
    flattened_requirements_without_editables = [
        requirement for requirement in flattened_requirements if not is_editable_requirement(requirement)]

    dependencies.extend(flattened_requirements_without_editables)

    for i, dep in enumerate(dependencies):
        if dep.startswith('"') and dep.endswith('"'):
            dependencies[i] = dep[1:-1]

    return build_string_from_array(dependencies)


def build_dependency_links_string(project):
    dependency_links = [
        dependency for dependency in project.dependencies
        if isinstance(dependency, Dependency) and dependency.url]
    requirements = [
        requirement for requirement in project.dependencies
        if isinstance(requirement, RequirementsFile)]

    editable_links_from_requirements = []
    for requirement in requirements:
        editables = [editable for editable in flatten_and_quote(requirement) if is_editable_requirement(editable)]
        editable_links_from_requirements.extend(
            [editable.replace("--editable ", "").replace("-e ", "") for editable in editables])

    if not dependency_links and not requirements:
        return "[]"

    def format_single_dependency(dependency):
        return '%s' % dependency.url

    all_dependency_links = [link for link in map(format_single_dependency, dependency_links)]
    all_dependency_links.extend(editable_links_from_requirements)

    for i, dep in enumerate(all_dependency_links):
        if dep.startswith('"') and dep.endswith('"'):
            all_dependency_links[i] = dep[1:-1]

    return build_string_from_array(all_dependency_links)


def build_scripts_string(project):
    scripts = [script for script in project.list_scripts()]

    scripts_dir = project.get_property("dir_dist_scripts")
    if scripts_dir:
        scripts = list(map(lambda s: os.path.join(scripts_dir, s), scripts))

    if len(scripts) > 0:
        return build_string_from_array(scripts)
    else:
        return '[]'


def build_data_files_string(project):
    indent = 8
    """
    data_files = [
      ('bin', ['foo','bar','hhrm'])
    ]
    """
    data_files = project.files_to_install
    if not len(data_files):
        return '[]'

    returnString = "[\n"

    for dataType, dataFiles in data_files:
        returnString += (" " * (indent+4)) + "('%s', ['" % dataType
        returnString += "', '".join(dataFiles)
        returnString += "']),\n"

    returnString = returnString[:-2] + "\n"
    returnString += " " * indent + "]"
    return returnString


def build_package_data_string(project):
    indent = 8

    sorted_keys = sorted(project.package_data.keys())

    package_data = project.package_data
    if package_data == {}:
        return "{}"

    returnString = "{\n"

    for pkgType in sorted_keys:
        returnString += " " * (indent+4)
        returnString += "'%s': " % pkgType
        returnString += "['"
        returnString += "', '".join(package_data[pkgType])
        returnString += "'],\n"

    returnString = returnString[:-2] + "\n"
    returnString += " " * indent + "}"

    return returnString


def build_packages_string(project):
    pkgs = [pkg for pkg in project.list_packages()]
    if len(pkgs) > 0:
        return build_string_from_array(pkgs)
    else:
        return '[]'


def build_modules_string(project):
    mods = [mod for mod in project.list_modules()]
    if len(mods) > 0:
        return build_string_from_array(mods)
    else:
        return '[]'


def build_console_scripts_string(project):
    console_scripts = project.get_property('distutils_console_scripts', [])

    if len(console_scripts) == 0:
        return "{}"

    indent = 12
    string = "{'console_scripts': "
    string += build_string_from_array(console_scripts, indent)
    string += "}"

    return string


def build_classifiers_string(project):
    classifiers = project.get_property('distutils_classifiers', [])
    return build_string_from_array(classifiers, indent=12)


def build_string_from_array(arr, indent=12):
    returnString = ""

    if len(arr) == 1:
        """
        arrays with one item contained on one line
        """
        if len(arr[0]) > 0:
            if is_notstr_iterable(arr[0]):
                returnString += "[" + build_string_from_array(arr[0], indent+4) + "]"
            else:
                returnString += "['%s']" % arr[0]
    elif len(arr) > 1:
        returnString = "[\n"

        for item in arr:
            if len(item) > 0:
                if is_notstr_iterable(item):
                    returnString += (" " * indent) + build_string_from_array(item, indent+4) + ",\n"
                else:
                    returnString += (" " * indent) + "'" + item + "',\n"

        returnString = returnString[:-2] + "\n"
        returnString += " " * (indent - 4)
        returnString += "]"

    return returnString


def build_string_from_dict(d, indent=12):
    mapStrings = []

    for k, v in d:
        mapStrings.append("'%s': '%s'" % (k, v))

    returnString = ""

    if len(mapStrings) > 0:

        joinString = ",\n"
        joinString += " " * indent

        returnString += "\n"
        returnString += " " * indent
        returnString += joinString.join(mapStrings)
        returnString += "\n"
        returnString += " " * (indent - 4)
        returnString += "}"

    return returnString
