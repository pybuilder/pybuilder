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
import re
import string
import subprocess
import sys
from datetime import datetime
from textwrap import dedent

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
from pybuilder.errors import BuildFailedException, MissingPrerequisiteException
from pybuilder.utils import (as_list,
                             is_string,
                             is_notstr_iterable,
                             get_dist_version_string,
                             safe_log_file_name,
                             assert_can_execute)
# Plugin install_dependencies_plugin can reload pip_common and pip_utils. Do not use from ... import ...
from pybuilder import pip_utils


use_plugin("python.core")

LEADING_TAB_RE = re.compile(r'^(\t*)')
DATA_FILES_PROPERTY = "distutils_data_files"
SETUP_TEMPLATE = string.Template("""#!/usr/bin/env python
$remove_hardlink_capabilities_for_shared_filesystems
from $module import setup
from $module.command.install import install as _install

class install(_install):
    def pre_install_script(self):
$preinstall_script

    def post_install_script(self):
$postinstall_script

    def run(self):
        self.pre_install_script()

        _install.run(self)

        self.post_install_script()

if __name__ == '__main__':
    setup(
        name = $name,
        version = $version,
        description = $summary,
        long_description = $description,
        author = $author,
        author_email = $author_email,
        license = $license,
        url = $url,
        scripts = $scripts,
        packages = $packages,
        namespace_packages = $namespace_packages,
        py_modules = $modules,
        classifiers = $classifiers,
        entry_points = $entry_points,
        data_files = $data_files,
        package_data = $package_data,
        install_requires = $dependencies,
        dependency_links = $dependency_links,
        zip_safe = True,
        cmdclass = {'install': install},
        keywords = $setup_keywords,
        python_requires = $python_requires,
        obsoletes = $obsoletes,
    )
""")


def default(value, default=""):
    if value is None:
        return default
    return value


def as_str(value):
    return repr(str(value))


@init
def initialize_distutils_plugin(project):
    project.plugin_depends_on("pypandoc", "~=1.3.0")

    project.set_property_if_unset("distutils_commands", ["sdist", "bdist_wheel"])
    project.set_property_if_unset("distutils_command_options", None)

    # Workaround for http://bugs.python.org/issue8876 , unable to build a bdist
    # on a filesystem that does not support hardlinks
    project.set_property_if_unset("distutils_issue8876_workaround_enabled", False)
    project.set_property_if_unset("distutils_classifiers", [
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python"
    ])
    project.set_property_if_unset("distutils_use_setuptools", True)
    project.set_property_if_unset("distutils_upload_repository", None)
    project.set_property_if_unset("distutils_upload_sign", False)
    project.set_property_if_unset("distutils_upload_sign_identity", None)

    project.set_property_if_unset("distutils_readme_description", False)
    project.set_property_if_unset("distutils_readme_file", "README.md")
    project.set_property_if_unset("distutils_description_overwrite", False)

    project.set_property_if_unset("distutils_console_scripts", None)
    project.set_property_if_unset("distutils_entry_points", None)
    project.set_property_if_unset("distutils_setup_keywords", None)


@after("prepare")
def set_description(project, logger):
    if project.get_property("distutils_readme_description"):
        try:
            assert_can_execute(["pandoc", "--version"], "pandoc", "distutils")
            doc_convert(project, logger)
        except (MissingPrerequisiteException, ImportError):
            logger.warn("Was unable to find pandoc or pypandoc and did not convert the documentation")


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
        "name": as_str(project.name),
        "version": as_str(project.dist_version),
        "summary": as_str(default(project.summary)),
        "description": as_str(default(project.description)),
        "author": as_str(author),
        "author_email": as_str(author_email),
        "license": as_str(default(project.license)),
        "url": as_str(default(project.url)),
        "scripts": build_scripts_string(project),
        "packages": build_packages_string(project),
        "namespace_packages": build_namespace_packages_string(project),
        "modules": build_modules_string(project),
        "classifiers": build_classifiers_string(project),
        "entry_points": build_entry_points_string(project),
        "data_files": build_data_files_string(project),
        "package_data": build_package_data_string(project),
        "dependencies": build_install_dependencies_string(project),
        "dependency_links": build_dependency_links_string(project),
        "remove_hardlink_capabilities_for_shared_filesystems": (
            "import os\ndel os.link"
            if project.get_property("distutils_issue8876_workaround_enabled")
            else ""),
        "preinstall_script": _normalize_setup_post_pre_script(project.setup_preinstall_script or "pass"),
        "postinstall_script": _normalize_setup_post_pre_script(project.setup_postinstall_script or "pass"),
        "setup_keywords": build_setup_keywords(project),
        "python_requires": as_str(default(project.requires_python)),
        "obsoletes": build_string_from_array(project.obsoletes)
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

    commands = [build_command_with_options(cmd, project.get_property("distutils_command_options"))
                for cmd in as_list(project.get_property("distutils_commands"))]
    execute_distutils(project, logger, commands, True)


@task("install")
def install_distribution(project, logger):
    logger.info("Installing project %s-%s", project.name, project.version)

    _prepare_reports_dir(project)
    outfile_name = project.expand_path("$dir_reports", "distutils",
                                       "pip_install_%s" % datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    pip_utils.pip_install(
        install_targets=project.expand_path("$dir_dist"),
        index_url=project.get_property("install_dependencies_index_url"),
        extra_index_url=project.get_property("install_dependencies_extra_index_url"),
        force_reinstall=True,
        logger=logger,
        verbose=project.get_property("verbose"),
        cwd=".",
        outfile_name=outfile_name,
        error_file_name=outfile_name)


@task("upload", description="Upload a project to PyPi.")
def upload(project, logger):
    repository = project.get_property("distutils_upload_repository")
    repository_args = []
    if repository:
        repository_args = ["-r", repository]

    upload_sign = project.get_property("distutils_upload_sign")
    upload_sign_args = []
    if upload_sign:
        upload_sign_args = ["--sign"]
        sign_identity = project.get_property("distutils_upload_sign_identity")
        if sign_identity:
            upload_sign_args += ["--identity", sign_identity]

    # Unfortunately, distutils/setuptools doesn't throw error if register fails
    # but upload command will fail if project will not be registered
    logger.info("Registering project %s-%s%s", project.name, project.version,
                (" into repository '%s'" % repository) if repository else "")
    register_cmd_line = [["register"] + repository_args]
    execute_distutils(project, logger, register_cmd_line, False)

    logger.info("Uploading project %s-%s%s%s%s", project.name, project.version,
                (" to repository '%s'" % repository) if repository else "",
                get_dist_version_string(project, " as version %s"),
                (" signing%s" % (" with %s" % sign_identity if sign_identity else "")) if upload_sign else "")
    upload_cmd_line = [build_command_with_options(cmd, project.get_property("distutils_command_options")) + ["upload"] +
                       repository_args + upload_sign_args
                       for cmd in as_list(project.get_property("distutils_commands"))]
    execute_distutils(project, logger, upload_cmd_line, True)


def build_command_with_options(command, distutils_command_options=None):
    commands = [command]
    if distutils_command_options:
        try:
            command_options = as_list(distutils_command_options[command])
            commands.extend(command_options)
        except KeyError:
            pass
    return commands


def execute_distutils(project, logger, distutils_commands, clean=False):
    reports_dir = _prepare_reports_dir(project)
    setup_script = project.expand_path("$dir_dist", "setup.py")

    for command in distutils_commands:
        logger.debug("Executing distutils command %s", command)
        if is_string(command):
            output_file_path = os.path.join(reports_dir, safe_log_file_name(command))
        else:
            output_file_path = os.path.join(reports_dir, safe_log_file_name("__".join(command)))
        with open(output_file_path, "w") as output_file:
            commands = [sys.executable, setup_script]
            if project.get_property("verbose"):
                commands.append("-v")
            if clean:
                commands.extend(["clean", "--all"])
            if is_string(command):
                commands.extend(command.split())
            else:
                commands.extend(command)
            return_code = _run_process_and_wait(commands, project.expand_path("$dir_dist"), output_file)
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
    return '%s%s' % (dependency.name, pip_utils.build_dependency_version_string(dependency))


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
        scripts = list(map(lambda s: '%s/%s' % (scripts_dir, s), scripts))

    return build_string_from_array(scripts)


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

    result = "[\n"

    for dataType, dataFiles in data_files:
        result += (" " * (indent + 4)) + "('%s', ['" % dataType
        result += "', '".join(dataFiles)
        result += "']),\n"

    result = result[:-2] + "\n"
    result += " " * indent + "]"
    return result


def build_package_data_string(project):
    indent = 8

    sorted_keys = sorted(project.package_data.keys())

    package_data = project.package_data
    if package_data == {}:
        return "{}"

    result = "{\n"

    for pkgType in sorted_keys:
        result += " " * (indent + 4)
        result += "'%s': " % pkgType
        result += "['"
        result += "', '".join(package_data[pkgType])
        result += "'],\n"

    result = result[:-2] + "\n"
    result += " " * indent + "}"

    return result


def build_namespace_packages_string(project):
    return build_string_from_array([pkg for pkg in project.explicit_namespaces])


def build_packages_string(project):
    return build_string_from_array([pkg for pkg in project.list_packages()])


def build_modules_string(project):
    return build_string_from_array([mod for mod in project.list_modules()])


def build_entry_points_string(project):
    console_scripts = project.get_property('distutils_console_scripts')
    entry_points = project.get_property('distutils_entry_points')
    if console_scripts is not None and entry_points is not None:
        raise BuildFailedException("'distutils_console_scripts' cannot be combined with 'distutils_entry_points'")

    if entry_points is None:
        entry_points = dict()

    if console_scripts is not None:
        entry_points['console_scripts'] = console_scripts

    if len(entry_points) == 0:
        return '{}'

    indent = 8
    result = "{\n"

    for k in sorted(entry_points.keys()):
        result += " " * (indent + 4)
        result += "'%s': %s" % (k, build_string_from_array(as_list(entry_points[k]), indent + 8)) + ",\n"

    result = result[:-2] + "\n"
    result += (" " * indent) + "}"

    return result


def build_setup_keywords(project):
    setup_keywords = project.get_property("distutils_setup_keywords")
    if not setup_keywords or not len(setup_keywords):
        return repr("")

    if isinstance(setup_keywords, (list, tuple)):
        return repr(" ".join(setup_keywords))

    return repr(setup_keywords)


def build_classifiers_string(project):
    classifiers = project.get_property('distutils_classifiers', [])
    return build_string_from_array(classifiers, indent=12)


def build_string_from_array(arr, indent=12):
    result = ""

    if len(arr) == 1:
        """
        arrays with one item contained on one line
        """
        if len(arr[0]) > 0:
            if is_notstr_iterable(arr[0]):
                result += "[" + build_string_from_array(arr[0], indent + 4) + "]"
            else:
                result += "['%s']" % arr[0]
        else:
            result = '[[]]'
    elif len(arr) > 1:
        result = "[\n"

        for item in arr:
            if is_notstr_iterable(item):
                result += (" " * indent) + build_string_from_array(item, indent + 4) + ",\n"
            else:
                result += (" " * indent) + "'" + item + "',\n"
        result = result[:-2] + "\n"
        result += " " * (indent - 4)
        result += "]"
    else:
        result = '[]'

    return result


def build_string_from_dict(d, indent=12):
    element_separator = ",\n"
    element_separator += " " * indent
    map_elements = []

    for k, v in d.items():
        map_elements.append("'%s': '%s'" % (k, v))

    result = ""

    if len(map_elements) > 0:
        result += "{\n"
        result += " " * indent
        result += element_separator.join(map_elements)
        result += "\n"
        result += " " * (indent - 4)
        result += "}"

    return result


def doc_convert(project, logger):
    import pypandoc
    readme_file = project.expand_path("$distutils_readme_file")
    logger.debug("Converting %s into RST format for PyPi documentation...", readme_file)
    description = pypandoc.convert_file(readme_file, "rst")
    if not hasattr(project, "description") or project.description is None or project.get_property(
            "distutils_description_overwrite"):
        setattr(project, "description", description)

    if not hasattr(project, "summary") or project.summary is None or project.get_property(
            "distutils_description_overwrite"):
        setattr(project, "summary", description.splitlines()[0].strip())


def _expand_leading_tabs(s, indent=4):
    def replace_tabs(match):
        return " " * (len(match.groups(0)) * indent)

    return "".join([LEADING_TAB_RE.sub(replace_tabs, line) for line in s.splitlines(True)])


def _normalize_setup_post_pre_script(s, indent=8):
    indent_str = " " * indent
    return "".join([indent_str + line if len(str.rstrip(line)) > 0 else line for line in
                    dedent(_expand_leading_tabs(s)).splitlines(True)])


def _run_process_and_wait(commands, cwd, stdout, stderr=None):
    process = subprocess.Popen(commands,
                               cwd=cwd,
                               stdout=stdout,
                               stderr=stderr or stdout,
                               shell=False)
    return process.wait()


def _prepare_reports_dir(project):
    reports_dir = project.expand_path("$dir_reports", "distutils")
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)
    return reports_dir
