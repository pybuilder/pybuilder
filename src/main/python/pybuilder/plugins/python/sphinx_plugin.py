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

"""Sphinx-plugin for PyBuilder to run a sphinx quickstart and generate the documentation once set up.
"""

from datetime import date
from os import mkdir
from os.path import join, dirname, relpath, exists
from shutil import rmtree

from pybuilder import scaffolding as SCAFFOLDING
from pybuilder.core import after, depends, init, task, use_plugin
from pybuilder.errors import BuildFailedException
from pybuilder.python_utils import symlink
from pybuilder.utils import (as_list,
                             tail_log)

__author__ = "Thomas Prebble", "Marcel Wolf", "Arcadiy Ivanov"

use_plugin("core")
use_plugin("python.core")

DEFAULT_SPHINX_OUTPUT_DIR = join(SCAFFOLDING.DEFAULT_DOCS_DIRECTORY, "_build")
SPHINX_PYB_CONFIG_MODULE = "sphinx_pyb_conf"
SPHINX_PYB_RUNTIME_DIR = ("$dir_target", "sphinx_pyb")
SPHINX_PYB_APIDOC_DIR = "apidoc"
SPHINX_PYB_RUNTIME_APIDOC_DIR = SPHINX_PYB_RUNTIME_DIR + (SPHINX_PYB_APIDOC_DIR,)
SPHINX_PYB_CONFIG_FILE_PATH = SPHINX_PYB_RUNTIME_DIR + (SPHINX_PYB_CONFIG_MODULE + ".py",)

SPHINX_DOC_BUILDER = "html"


@init
def initialize_sphinx_plugin(project):
    default_project_version = project.version
    default_project_name = project.name
    default_doc_author = ", ".join([author.name for author in project.authors])

    project.plugin_depends_on("sphinx")
    project.set_property_if_unset(
        "sphinx_source_dir", SCAFFOLDING.DEFAULT_DOCS_DIRECTORY)
    project.set_property_if_unset(
        "sphinx_output_dir", DEFAULT_SPHINX_OUTPUT_DIR)
    project.set_property_if_unset(
        "sphinx_config_path", SCAFFOLDING.DEFAULT_DOCS_DIRECTORY)
    project.set_property_if_unset(
        "sphinx_output_per_builder", False)
    project.set_property_if_unset(
        "sphinx_doc_author", default_doc_author)
    project.set_property_if_unset(
        "sphinx_doc_builder", SPHINX_DOC_BUILDER)
    project.set_property_if_unset(
        "sphinx_project_name", default_project_name)
    project.set_property_if_unset(
        "sphinx_project_version", default_project_version)
    project.set_property_if_unset(
        "sphinx_run_apidoc", False)

    # Extra arguments such as -d, -e, -M etc to add to Sphinx apidoc run
    project.set_property_if_unset(
        "sphinx_apidoc_extra_args", [])

    # Extra arguments such as -E, -D etc to add to Sphinx build run
    project.set_property_if_unset(
        "sphinx_build_extra_args", [])

    copyright = "%s, %s" % (date.today().year, project.get_property("sphinx_doc_author"))
    project.set_property_if_unset(
        "sphinx_project_conf", {
            "extensions": [
                "sphinx.ext.autodoc",
                "sphinx.ext.todo",
                "sphinx.ext.viewcode",
            ],
            "templates_path": ["_templates"],
            "source_suffix": ".rst",
            "master_doc": "index",
            "project": project.get_property("sphinx_project_name"),
            "copyright": copyright,
            "author": project.get_property("sphinx_doc_author"),
            "version": project.get_property("sphinx_project_version"),
            "release": project.dist_version,
            "language": "en",
            "exclude_patterns": ["_build", "Thumbs.db", ".DS_Store"],
            "pygments_style": "sphinx",
            "todo_include_todos": True,
            "html_static_path": ["_static"],
            "htmlhelp_basename": "%sdoc" % project.get_property("sphinx_project_name"),
            "latex_elements": {

            },

            "latex_documents": [
                ("index",
                 "%s.tex" % project.get_property("sphinx_project_name"),
                 "%s Documentation" % project.get_property("sphinx_project_name"),
                 project.get_property("sphinx_doc_author"), "manual"),
            ],
            "man_pages": [
                ("index",
                 project.get_property("sphinx_project_name"),
                 "%s Documentation" % project.get_property("sphinx_project_name"),
                 [project.get_property("sphinx_doc_author")], 1)
            ],
            "texinfo_documents": [
                ("index",
                 project.get_property("sphinx_project_name"),
                 "%s Documentation" % project.get_property("sphinx_project_name"),
                 project.get_property("sphinx_doc_author"),
                 project.get_property("sphinx_project_name"),
                 "One line description of project.",
                 "Miscellaneous"),
            ],
            "epub_title": project.get_property("sphinx_project_name"),
            "epub_author": project.get_property("sphinx_doc_author"),
            "epub_publisher": project.get_property("sphinx_doc_author"),
            "epub_copyright": copyright,
            "epub_exclude_files": ["search.html"]
        }
    )


@after("prepare")
def assert_sphinx_is_available(project, logger, reactor):
    """Asserts that the sphinx-build script is available.
    """
    logger.debug("Checking if sphinx-build and sphinx-apidoc are available.")

    reactor.pybuilder_venv.verify_can_execute(["sphinx-build", "--version"], "sphinx-build",
                                              "plugin python.sphinx")
    reactor.pybuilder_venv.verify_can_execute(["sphinx-apidoc", "--version"], "sphinx-apidoc",
                                              "plugin python.sphinx")


@after("prepare")
def assert_sphinx_quickstart_is_available(project, logger, reactor):
    """Asserts that the sphinx-quickstart script is available.
    """
    logger.debug("Checking if sphinx-quickstart is available.")

    reactor.pybuilder_venv.verify_can_execute(["sphinx-quickstart", "--version"], "sphinx-quickstart",
                                              "plugin python.sphinx")


def run_sphinx_build(build_command, task_name, logger, project, reactor, builder=None):
    logger.info("Running %s" % task_name)
    log_file = project.expand_path("$dir_target", "reports", task_name)

    build_command = reactor.pybuilder_venv.executable + ["-c"] + build_command

    exit_code = reactor.pybuilder_venv.execute_command(build_command, log_file, shell=False)
    if exit_code != 0:
        raise BuildFailedException("Sphinx build command failed. See %s for full details:\n%s",
                                   log_file,
                                   tail_log(log_file))


@task("sphinx_generate_documentation", "Generates documentation with sphinx")
@depends("prepare")
def sphinx_generate(project, logger, reactor):
    """Runs sphinx-build against rst sources for the given project.
    """
    sphinx_pyb_dir = project.expand_path(*SPHINX_PYB_RUNTIME_DIR)
    if exists(sphinx_pyb_dir):
        logger.debug("Removing %s", sphinx_pyb_dir)
        rmtree(sphinx_pyb_dir)
    logger.debug("Creating %s", sphinx_pyb_dir)
    mkdir(sphinx_pyb_dir)

    generate_sphinx_pyb_runtime_config(project, logger)

    generate_sphinx_apidocs(project, logger, reactor)

    builders = as_list(project.get_property("sphinx_doc_builder"))
    for builder in builders:
        build_command = get_sphinx_build_command(project, logger, builder)
        run_sphinx_build(build_command, "sphinx_%s" % builder, logger, project, reactor, builder=builder)


@task("sphinx_quickstart", "starts a new sphinx project")
@depends("prepare")
def sphinx_quickstart_generate(project, logger, reactor):
    """Runs sphinx-build against rst sources for the given project.
    """
    build_command = get_sphinx_quickstart_command(project)
    run_sphinx_build(build_command, "sphinx-quickstart", logger, project, reactor)


@task("sphinx_pyb_quickstart", "starts a new PyB-specific Sphinx project")
@depends("prepare")
def sphinx_pyb_quickstart_generate(project, logger, reactor):
    """Generates PyB-specific quickstart

    Actually sticks the PyB-specific paths and generated stub into the configuration.
    """
    sphinx_quickstart_generate(project, logger, reactor)  # If this fails we won't touch the config directory further

    sphinx_config_path = project.expand_path("$sphinx_config_path")
    sphinx_pyb_config_path = project.expand_path(*SPHINX_PYB_CONFIG_FILE_PATH)
    sphinx_pyb_config_dir = dirname(sphinx_pyb_config_path)
    sphinx_pyb_rel_dir = relpath(sphinx_pyb_config_dir, sphinx_config_path)

    content = """\
# Automatically generated by PyB
import sys
from os.path import normcase as nc, normpath as np, join as jp, dirname, exists

sphinx_pyb_dir = nc(np(jp(dirname(__file__) if __file__ else '.', %(sphinx_pyb_rel_dir)r)))
sphinx_pyb_module = %(sphinx_pyb_module_name)r
sphinx_pyb_module_file = nc(np(jp(sphinx_pyb_dir, sphinx_pyb_module + '.py')))

sys.path.insert(0, sphinx_pyb_dir)

if not exists(sphinx_pyb_module_file):
    raise RuntimeError("No PyB-based Sphinx configuration found in " + sphinx_pyb_module_file)

from %(sphinx_pyb_module_name)s import *

# Overwrite PyB-settings here statically if that's the thing that you want
""" % {
        "sphinx_pyb_rel_dir": sphinx_pyb_rel_dir,
        "sphinx_pyb_module_name": SPHINX_PYB_CONFIG_MODULE
    }

    sphinx_config_dir = project.expand_path("$sphinx_config_path")
    conf_file = join(sphinx_config_dir, "conf.py")
    with open(conf_file, "wt") as conf_py:
        conf_py.write(content)

    target_apidoc_dir = join(sphinx_pyb_rel_dir, SPHINX_PYB_APIDOC_DIR)
    source_apidoc_link = project.expand_path("$sphinx_source_dir", SPHINX_PYB_APIDOC_DIR)
    if not exists(source_apidoc_link):
        try:
            symlink(target_apidoc_dir, source_apidoc_link, target_is_directory=True)
        except TypeError:
            symlink(target_apidoc_dir, source_apidoc_link)


def get_sphinx_quickstart_command(project):
    """Builds the sphinx-quickstart command using project properties.
        sphinx-quickstart parameters:
        :param -q: Quiet mode that will skips interactive wizard to specify options.
        :param -p: Project name will be set.
        :param -a: Author names.
        :param -v: Version of project.
    """
    options = [_get_sphinx_launch_cmd("sphinx.cmd.quickstart", "main", "sphinx-quickstart"),
               "-q",
               "-p", project.get_property("sphinx_project_name"),
               "-a", project.get_property("sphinx_doc_author"),
               "-v", project.get_property("sphinx_project_version"),
               project.expand_path("$sphinx_source_dir")]
    return options


def get_sphinx_build_command(project, logger, builder):
    """Builds the sphinx-build command using properties.
    """
    options = [_get_sphinx_launch_cmd("sphinx.cmd.build", "main", "sphinx-build"),
               "-b", builder
               ]

    verbose = None
    if project.get_property("verbose"):
        verbose = "-v"
    if logger.level == logger.DEBUG:
        verbose = "-vvvv"
    if verbose:
        options.append(verbose)

    options += as_list(project.get_property("sphinx_build_extra_args"))

    options.append(project.expand_path("$sphinx_config_path"))

    if len(as_list(project.get_property("sphinx_doc_builder"))) > 1 or \
            project.get_property("sphinx_output_per_builder"):
        options.append(project.expand_path("$sphinx_output_dir", builder))
    else:
        options.append(project.expand_path("$sphinx_output_dir"))

    return options


def get_sphinx_apidoc_command(project, reactor):
    implicit_namespaces = False
    try:
        import sphinx

        if reactor.pybuilder_venv.version[:2] >= (3, 3) and sphinx.version_info[:2] >= (1, 5):
            implicit_namespaces = True
    except ImportError:
        pass

    options = [_get_sphinx_launch_cmd("sphinx.ext.apidoc", "main", "sphinx-apidoc"),
               "-H", project.get_property("sphinx_project_name")]

    if implicit_namespaces:
        options.append("--implicit-namespaces")

    options += as_list(project.get_property("sphinx_apidoc_extra_args"))

    options += ["-o",
                project.expand_path(*SPHINX_PYB_RUNTIME_APIDOC_DIR),
                project.expand_path("$dir_source_main_python")]
    return options


def generate_sphinx_pyb_runtime_config(project, logger):
    sphinx_pyb_conf_path = project.expand_path(*SPHINX_PYB_CONFIG_FILE_PATH)

    logger.debug("Generating PyB-based Sphinx runtime config at %s", sphinx_pyb_conf_path)
    with open(sphinx_pyb_conf_path, "wt") as sphinx_pyb_conf:
        for k, v in project.get_property("sphinx_project_conf").items():
            sphinx_pyb_conf.write("%s = %r\n" % (k, v))
        sphinx_pyb_conf.write("\nimport sys\nsys.path.insert(0, %r)\n" % project.expand_path("$dir_source_main_python"))


def generate_sphinx_apidocs(project, logger, reactor):
    if not project.get_property("sphinx_run_apidoc"):
        logger.debug("Sphinx API Doc is turned off - skipping")
        return

    apidoc_dir = project.expand_path(*SPHINX_PYB_RUNTIME_APIDOC_DIR)
    if exists(apidoc_dir):
        logger.debug("Removing %s", apidoc_dir)
        rmtree(apidoc_dir)
    logger.debug("Creating %s", apidoc_dir)
    mkdir(apidoc_dir)

    build_command = get_sphinx_apidoc_command(project, reactor)
    logger.debug("Generating Sphinx API Doc")
    run_sphinx_build(build_command, "sphinx-apidoc", logger, project, reactor)


def _get_sphinx_launch_cmd(module, func, script_name):
    return "import sys; from %(module)s import %(func)s; " \
           "sys.argv[0] = %(script_name)r; sys.exit(%(func)s())" % dict(module=module,
                                                                        func=func,
                                                                        script_name=script_name)
