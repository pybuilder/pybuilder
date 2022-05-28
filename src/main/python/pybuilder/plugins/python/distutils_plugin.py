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

import io
import os
import re
import string
from datetime import datetime
from textwrap import dedent

from pybuilder import pip_utils
from pybuilder.core import (after,
                            before,
                            use_plugin,
                            init,
                            task,
                            RequirementsFile,
                            Dependency)
from pybuilder.errors import BuildFailedException, MissingPrerequisiteException
from pybuilder.python_utils import StringIO
from pybuilder.utils import (as_list,
                             is_string,
                             is_notstr_iterable,
                             get_dist_version_string,
                             safe_log_file_name,
                             tail_log)

use_plugin("python.core")

LEADING_TAB_RE = re.compile(r'^(\t*)')
DATA_FILES_PROPERTY = "distutils_data_files"
SETUP_TEMPLATE = string.Template("""#!/usr/bin/env python
#   -*- coding: utf-8 -*-
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
        long_description_content_type = $description_content_type,
        classifiers = $classifiers,
        keywords = $setup_keywords,

        author = $author,
        author_email = $author_email,
        maintainer = $maintainer,
        maintainer_email = $maintainer_email,

        license = $license,

        url = $url,
        project_urls = $project_urls,

        scripts = $scripts,
        packages = $packages,
        namespace_packages = $namespace_packages,
        py_modules = $modules,
        entry_points = $entry_points,
        data_files = $data_files,
        package_data = $package_data,
        install_requires = $dependencies,
        dependency_links = $dependency_links,
        zip_safe = $zip_safe,
        cmdclass = {'install': install},
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
    project.plugin_depends_on("pypandoc", "~=1.4")
    project.plugin_depends_on("setuptools", ">=38.6.0")
    project.plugin_depends_on("twine", ">=1.15.0")
    project.plugin_depends_on("wheel", ">=0.34.0")

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

    project.set_property_if_unset("distutils_fail_on_warnings", False)

    project.set_property_if_unset("distutils_upload_register", False)
    project.set_property_if_unset("distutils_upload_repository", None)
    project.set_property_if_unset("distutils_upload_repository_key", None)
    project.set_property_if_unset("distutils_upload_sign", False)
    project.set_property_if_unset("distutils_upload_sign_identity", None)
    project.set_property_if_unset("distutils_upload_skip_existing", False)

    project.set_property_if_unset("distutils_readme_description", False)
    project.set_property_if_unset("distutils_readme_file", "README.md")
    project.set_property_if_unset("distutils_readme_file_convert", False)
    project.set_property_if_unset("distutils_readme_file_type", None)
    project.set_property_if_unset("distutils_readme_file_encoding", None)
    project.set_property_if_unset("distutils_readme_file_variant", None)
    project.set_property_if_unset("distutils_summary_overwrite", False)
    project.set_property_if_unset("distutils_description_overwrite", False)

    project.set_property_if_unset("distutils_console_scripts", None)
    project.set_property_if_unset("distutils_entry_points", None)
    project.set_property_if_unset("distutils_setup_keywords", None)
    project.set_property_if_unset("distutils_zip_safe", True)


@after("prepare")
def set_description(project, logger, reactor):
    if project.get_property("distutils_readme_description"):
        description = None
        if project.get_property("distutils_readme_file_convert"):
            try:
                reactor.pybuilder_venv.verify_can_execute(["pandoc", "--version"], "pandoc", "distutils")
                description = doc_convert(project, logger)
            except (MissingPrerequisiteException, ImportError):
                logger.warn("Was unable to find pandoc or pypandoc and did not convert the documentation")
        else:
            with io.open(project.expand_path("$distutils_readme_file"), "rt",
                         encoding=project.get_property("distutils_readme_file_encoding")) as f:
                description = f.read()

        if description:
            if (not hasattr(project, "summary") or
                    project.summary is None or
                    project.get_property("distutils_summary_overwrite")):
                setattr(project, "summary", description.splitlines()[0].strip())

            if (not hasattr(project, "description") or
                    project.description is None or
                    project.get_property("distutils_description_overwrite")):
                setattr(project, "description", description)

    if (not hasattr(project, "description") or
            not project.description):
        if hasattr(project, "summary") and project.summary:
            description = project.summary
        else:
            description = project.name

        setattr(project, "description", description)

    warn = False
    if len(project.summary) >= 512:
        logger.warn("Project summary SHOULD be shorter than 512 characters per PEP-426")
        warn = True

    if "\n" in project.summary or "\r" in project.summary:
        logger.warn("Project summary SHOULD NOT contain new-line characters per PEP-426")
        warn = True

    if len(project.summary) >= 2048:
        raise BuildFailedException("Project summary MUST NOT be shorter than 2048 characters per PEP-426")

    if warn and project.get_property("distutils_fail_on_warnings"):
        raise BuildFailedException("Distutil plugin warnings caused a build failure. Please see warnings above.")


@after("package")
def write_setup_script(project, logger):
    setup_script = project.expand_path("$dir_dist", "setup.py")
    logger.info("Writing setup.py as %s", setup_script)

    with io.open(setup_script, "wt", encoding="utf-8") as setup_file:
        script = render_setup_script(project)
        setup_file.write(script)

    os.chmod(setup_script, 0o755)


def render_setup_script(project):
    author = ", ".join(map(lambda a: a.name, project.authors))
    author_email = ", ".join(map(lambda a: a.email, project.authors))
    maintainer = ", ".join(map(lambda a: a.name, project.maintainers))
    maintainer_email = ",".join(map(lambda a: a.email, project.maintainers))

    template_values = {
        "module": "setuptools" if project.get_property("distutils_use_setuptools") else "distutils.core",
        "name": as_str(project.name),
        "version": as_str(project.dist_version),
        "summary": as_str(default(project.summary)),
        "description": as_str(default(project.description)),
        "description_content_type": repr(_get_description_content_type(project)),
        "author": as_str(author),
        "author_email": as_str(author_email),
        "maintainer": as_str(maintainer),
        "maintainer_email": as_str(maintainer_email),
        "license": as_str(default(project.license)),
        "url": as_str(default(project.url)),
        "project_urls": build_map_string(project.urls),
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
        "obsoletes": build_string_from_array(project.obsoletes),
        "zip_safe": project.get_property("distutils_zip_safe")
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


@before("publish")
def build_binary_distribution(project, logger, reactor):
    logger.info("Building binary distribution in %s",
                project.expand_path("$dir_dist"))

    commands = [build_command_with_options(cmd, project.get_property("distutils_command_options"))
                for cmd in as_list(project.get_property("distutils_commands"))]
    execute_distutils(project, logger, reactor.pybuilder_venv, commands, True)
    upload_check(project, logger, reactor)


@task("install")
def install_distribution(project, logger, reactor):
    logger.info("Installing project %s-%s", project.name, project.version)

    _prepare_reports_dir(project)
    outfile_name = project.expand_path("$dir_reports", "distutils",
                                       "pip_install_%s" % datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    pip_utils.pip_install(
        install_targets=project.expand_path("$dir_dist"),
        python_env=reactor.python_env_registry["system"],
        index_url=project.get_property("install_dependencies_index_url"),
        extra_index_url=project.get_property("install_dependencies_extra_index_url"),
        force_reinstall=True,
        logger=logger,
        verbose=project.get_property("pip_verbose"),
        cwd=".",
        outfile_name=outfile_name,
        error_file_name=outfile_name)


@task("upload", description="Upload a project to PyPi.")
def upload(project, logger, reactor):
    repository = project.get_property("distutils_upload_repository")
    repository_args = []
    if repository:
        repository_args = ["--repository-url", repository]
    else:
        repository_key = project.get_property("distutils_upload_repository_key")
        if repository_key:
            repository_args = ["--repository", repository_key]

    upload_sign = project.get_property("distutils_upload_sign")
    sign_identity = project.get_property("distutils_upload_sign_identity")
    upload_sign_args = []
    if upload_sign:
        upload_sign_args = ["--sign"]
        if sign_identity:
            upload_sign_args += ["--identity", sign_identity]

    if project.get_property("distutils_upload_register"):
        logger.info("Registering project %s-%s%s", project.name, project.version,
                    (" into repository '%s'" % repository) if repository else "")
        execute_twine(project, logger, reactor.pybuilder_venv, repository_args, "register")

    skip_existing = project.get_property("distutils_upload_skip_existing")
    logger.info("Uploading project %s-%s%s%s%s%s", project.name, project.version,
                (" to repository '%s'" % repository) if repository else "",
                get_dist_version_string(project, " as version %s"),
                (" signing%s" % (" with %s" % sign_identity if sign_identity else "")) if upload_sign else "",
                (", will skip existing" if skip_existing else ""))

    upload_cmd_args = repository_args + upload_sign_args
    if skip_existing:
        upload_cmd_args.append("--skip-existing")

    execute_twine(project, logger, reactor.pybuilder_venv, upload_cmd_args, "upload")


def upload_check(project, logger, reactor):
    logger.info("Running Twine check for generated artifacts")
    execute_twine(project, logger, reactor.pybuilder_venv, [], "check")


def render_manifest_file(project):
    manifest_content = StringIO()

    for included_file in project.manifest_included_files:
        manifest_content.write("include %s\n" % included_file)

    for directory, pattern_list in project.manifest_included_directories:
        patterns = ' '.join(pattern_list)
        manifest_content.write("recursive-include %s %s\n" % (directory, patterns))

    return manifest_content.getvalue()


def build_command_with_options(command, distutils_command_options=None):
    commands = [command]
    if distutils_command_options:
        try:
            command_options = as_list(distutils_command_options[command])
            commands.extend(command_options)
        except KeyError:
            pass
    return commands


def execute_distutils(project, logger, python_env, distutils_commands, clean=False):
    reports_dir = _prepare_reports_dir(project)
    setup_script = project.expand_path("$dir_dist", "setup.py")

    for command in distutils_commands:
        if is_string(command):
            out_file = os.path.join(reports_dir, safe_log_file_name(command))
        else:
            out_file = os.path.join(reports_dir, safe_log_file_name("__".join(command)))
        with open(out_file, "w") as out_f:
            commands = python_env.executable + [setup_script]
            if project.get_property("verbose"):
                commands.append("-v")
            if clean:
                commands.extend(["clean", "--all"])
            if is_string(command):
                commands.extend(command.split())
            else:
                commands.extend(command)
            logger.debug("Executing distutils command: %s", commands)
            return_code = python_env.run_process_and_wait(commands, project.expand_path("$dir_dist"), out_f)
            if return_code != 0:
                raise BuildFailedException(
                    "Error while executing setup command %s. See %s for full details:\n%s",
                    command, out_file, tail_log(out_file))


def execute_twine(project, logger, python_env, command_args, command):
    reports_dir = _prepare_reports_dir(project)
    dist_artifact_dir, artifacts = _get_generated_artifacts(project, logger)

    if command == "register":
        for artifact in artifacts:
            out_file = os.path.join(reports_dir,
                                    safe_log_file_name("twine_%s_%s.log" % (command, os.path.basename(artifact))))
            _execute_twine(project, logger, python_env,
                           [command] + command_args + [artifact], dist_artifact_dir, out_file)
    else:
        out_file = os.path.join(reports_dir, safe_log_file_name("twine_%s.log" % command))
        _execute_twine(project, logger, python_env,
                       [command] + command_args + artifacts, dist_artifact_dir, out_file)


def _execute_twine(project, logger, python_env, command, work_dir, out_file):
    with open(out_file, "w") as out_f:
        commands = python_env.executable + ["-m", "twine"] + command
        logger.debug("Executing Twine: %s", commands)
        return_code = python_env.run_process_and_wait(commands, work_dir, out_f)
        if return_code != 0:
            raise BuildFailedException(
                "Error while executing Twine %s. See %s for full details:\n%s", command, out_file, tail_log(out_file))


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
        scripts = list(map(lambda s: '{}/{}'.format(scripts_dir, s), scripts))

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
    package_data = project.package_data
    if not package_data:
        return "{}"

    indent = 8

    sorted_keys = sorted(project.package_data.keys())

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


def build_map_string(m):
    if not m:
        return "{}"

    indent = 8

    sorted_keys = sorted(m.keys())

    result = "{\n"

    for k in sorted_keys:
        result += " " * (indent + 4)
        result += "%r: %r,\n" % (k, m[k])

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
    classifiers = project.get_property("distutils_classifiers", [])
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
    return pypandoc.convert_file(readme_file, "rst")


def _expand_leading_tabs(s, indent=4):
    def replace_tabs(match):
        return " " * (len(match.groups(0)) * indent)

    return "".join([LEADING_TAB_RE.sub(replace_tabs, line) for line in s.splitlines(True)])


def _normalize_setup_post_pre_script(s, indent=8):
    indent_str = " " * indent
    return "".join([indent_str + line if len(str.rstrip(line)) > 0 else line for line in
                    dedent(_expand_leading_tabs(s)).splitlines(True)])


def _prepare_reports_dir(project):
    reports_dir = project.expand_path("$dir_reports", "distutils")
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)
    return reports_dir


def _get_description_content_type(project):
    file_type = project.get_property("distutils_readme_file_type")
    file_encoding = project.get_property("distutils_readme_file_encoding")
    file_variant = project.get_property("distutils_readme_file_variant")

    if not file_type:
        if project.get_property("distutils_readme_description"):
            readme_file_ci = project.get_property("distutils_readme_file").lower()
            if readme_file_ci.endswith("md"):
                file_type = "text/markdown"
            elif readme_file_ci.endswith("rst"):
                file_type = "text/x-rst"
            else:
                file_type = "text/plain"

    if file_encoding:
        file_encoding = file_encoding.upper()

    if file_type == "text/markdown":
        if file_variant:
            file_variant = file_variant.upper()

    if file_type:
        return "%s%s%s" % (file_type,
                           "; charset=%s" % file_encoding if file_encoding else "",
                           "; variant=%s" % file_variant if file_variant else "")


def _get_generated_artifacts(project, logger):
    dist_artifact_dir = project.expand_path("$dir_dist", "dist")

    artifacts = [os.path.join(dist_artifact_dir, artifact) for artifact in list(os.walk(dist_artifact_dir))[0][2]]
    return dist_artifact_dir, artifacts
