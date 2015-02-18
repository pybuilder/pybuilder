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

import os
import string
import subprocess
import sys

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO

from pybuilder.core import (after,
                            before,
                            use_plugin,
                            init,
                            RequirementsFile,
                            Dependency)
from pybuilder.errors import BuildFailedException
from pybuilder.utils import as_list

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
          entry_points={
          'console_scripts':
              [$console_scripts]
          },
          $data_files   #  data files
          $package_data   # package data
          $dependencies
          $dependency_links
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


@after("package")
def write_setup_script(project, logger):
    setup_script = project.expand_path("$dir_dist/setup.py")
    logger.info("Writing setup.py as %s", setup_script)

    with open(setup_script, "w") as setup_file:
        setup_file.write(render_setup_script(project))

    os.chmod(setup_script, 0o755)


def render_setup_script(project):
    author = ", ".join(map(lambda a: a.name, project.authors))
    author_email = ", ".join(map(lambda a: a.email, project.authors))
    console_scripts = project.get_property("distutils_console_scripts", [])

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
        "packages": str([package for package in project.list_packages()]),
        "modules": str([module for module in project.list_modules()]),
        "classifiers": project.get_property("distutils_classifiers"),
        "console_scripts": ",".join(["'%s'" % mapping for mapping in console_scripts]),
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
    if len(project.manifest_included_files) == 0:
        logger.debug("No data to write into MANIFEST.in")
        return

    logger.debug("Files included in MANIFEST.in: %s" %
                 project.manifest_included_files)

    manifest_filename = project.expand_path("$dir_dist/MANIFEST.in")
    logger.info("Writing MANIFEST.in as %s", manifest_filename)

    with open(manifest_filename, "w") as manifest_file:
        manifest_file.write(render_manifest_file(project))

    os.chmod(manifest_filename, 0o664)


def render_manifest_file(project):
    manifest_content = StringIO()

    for included_file in project.manifest_included_files:
        manifest_content.write("include %s\n" % included_file)

    return manifest_content.getvalue()


@before("publish")
def build_binary_distribution(project, logger):
    reports_dir = project.expand_path("$dir_reports/distutils")
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)

    setup_script = project.expand_path("$dir_dist/setup.py")

    logger.info("Building binary distribution in %s",
                project.expand_path("$dir_dist"))

    commands = as_list(project.get_property("distutils_commands"))

    for command in commands:
        logger.debug("Executing distutils command %s", command)
        output_file_path = os.path.join(reports_dir, command.replace("/", ""))
        with open(output_file_path, "w") as output_file:
            commands = [sys.executable, setup_script]
            commands.extend(command.split())
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


def flatten_and_quote(requirements_file):
    with open(requirements_file.name, 'r') as requirements_file:
        requirements = [requirement.strip("\n") for requirement in requirements_file.readlines()]
        requirements = [requirement for requirement in requirements if requirement]
        return quote(strip_comments(requirements))


def format_single_dependency(dependency):
    return '"%s%s"' % (dependency.name, build_dependency_version_string(dependency))


def build_install_dependencies_string(project):
    dependencies = [
        dependency for dependency in project.dependencies
        if isinstance(dependency, Dependency) and not dependency.url]
    requirements = [
        requirements for requirements in project.dependencies
        if isinstance(requirements, RequirementsFile)]
    if not dependencies and not requirements:
        return ""

    dependencies = [format_single_dependency(dependency) for dependency in dependencies]
    requirements = [strip_comments(flatten_and_quote(requirement)) for requirement in requirements]
    flattened_requirements = [dependency for dependency_list in requirements for dependency in dependency_list]

    dependencies.extend(flattened_requirements)

    result = "install_requires = [ "
    result += ", ".join(dependencies)
    result += " ],"
    return result


def build_dependency_links_string(project):
    dependency_links = [
        dependency for dependency in project.dependencies
        if isinstance(dependency, Dependency) and dependency.url]
    if not dependency_links:
        return ""

    def format_single_dependency(dependency):
        return '"%s"' % dependency.url

    result = "dependency_links = [ "
    result += ", ".join(map(format_single_dependency, dependency_links))
    result += " ],"
    return result


def build_scripts_string(project):
    scripts = [script for script in project.list_scripts()]

    scripts_dir = project.get_property("dir_dist_scripts")
    if scripts_dir:
        scripts = list(map(lambda s: os.path.join(scripts_dir, s), scripts))

    return str(scripts)


def build_data_files_string(project):
    data_files = project.files_to_install

    if not len(data_files):
        return ""

    return "data_files = %s," % str(data_files)


def build_package_data_string(project):
    package_data = project.package_data
    if package_data == {}:
        return ""
    package_data_string = "package_data = {"

    sorted_keys = sorted(package_data.keys())
    last_element = sorted_keys[-1]

    for key in sorted_keys:
        package_data_string += "'%s': %s" % (key, str(package_data[key]))

        if key is not last_element:
            package_data_string += ", "

    package_data_string += "},"
    return package_data_string
