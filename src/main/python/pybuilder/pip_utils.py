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
import sys

from pip._vendor.packaging.specifiers import SpecifierSet, InvalidSpecifier
from pip._vendor.packaging.version import Version, InvalidVersion
from pip.commands.show import search_packages_info

try:
    # This is the path for pip 7.x
    from pip._vendor.pkg_resources import _initialize_master_working_set

    pip_working_set_init = _initialize_master_working_set
except ImportError:
    # This is the path for pip 6.x
    from pip._vendor import pkg_resources

    pip_working_set_init = pkg_resources

from pybuilder.core import Dependency, RequirementsFile
from pybuilder.utils import execute_command, as_list

PIP_EXEC_STANZA = [sys.executable, "-m", "pip.__main__"]
__RE_PIP_PACKAGE_VERSION = re.compile(r"^Version:\s+(.+)$", re.MULTILINE)


def build_dependency_version_string(mixed):
    if isinstance(mixed, Dependency):
        version = mixed.version
    else:
        version = mixed

    if not version:
        return ""

    try:
        return ">=%s" % Version(version)
    except InvalidVersion:
        try:
            return str(SpecifierSet(version))
        except InvalidSpecifier:
            raise ValueError("'%s' must be either PEP 0440 version or a version specifier set")


def pip_install(install_targets, index_url=None, extra_index_url=None, upgrade=False, insecure_installs=None,
                force_reinstall=False, target_dir=None, verbose=False, logger=None, outfile_name=None,
                error_file_name=None, env=None, cwd=None):
    pip_command_line = list()
    pip_command_line.extend(PIP_EXEC_STANZA)
    pip_command_line.append("install")
    pip_command_line.extend(build_pip_install_options(index_url,
                                                      extra_index_url,
                                                      upgrade,
                                                      insecure_installs,
                                                      force_reinstall,
                                                      target_dir,
                                                      verbose
                                                      ))
    for install_target in as_list(install_targets):
        pip_command_line.extend(as_pip_install_target(install_target))

    if env is None:
        env = os.environ

    if logger:
        logger.debug("Invoking pip: %s", pip_command_line)
    return execute_command(pip_command_line, outfile_name=outfile_name, env=env, cwd=cwd,
                           error_file_name=error_file_name, shell=False)


def build_pip_install_options(index_url=None, extra_index_url=None, upgrade=False, insecure_installs=None,
                              force_reinstall=False, target_dir=None, verbose=False):
    options = []
    if index_url:
        options.append("--index-url")
        options.append(index_url)
        if extra_index_url:
            options.append("--extra-index-url")
            options.append(extra_index_url)

    if upgrade:
        options.append("--upgrade")

    if verbose:
        options.append("--verbose")

    if force_reinstall:
        options.append("--force-reinstall")

    if target_dir:
        options.append("-t")
        options.append(target_dir)

    if _pip_disallows_insecure_packages_by_default() and insecure_installs:
        for insecure_install in insecure_installs:
            arguments_for_insecure_installation = ["--allow-unverified", insecure_install,
                                                   "--allow-external", insecure_install]
            options.extend(arguments_for_insecure_installation)

    return options


def as_pip_install_target(mixed):
    if isinstance(mixed, RequirementsFile):
        return ["-r", mixed.name]
    if isinstance(mixed, Dependency):
        if mixed.url:
            return [mixed.url]
        else:
            return ["{0}{1}".format(mixed.name, build_dependency_version_string(mixed))]
    return [str(mixed)]


def _pip_disallows_insecure_packages_by_default():
    import pip
    # (2014-01-01) BACKWARD INCOMPATIBLE pip no longer will scrape insecure external urls by default
    # nor will it install externally hosted files by default
    # Also pip v1.1 for example has no __version__
    return hasattr(pip, "__version__") and pip.__version__ >= '1.5'


def get_package_version(mixed, logger=None):
    def normalize_dependency_package(mixed):
        if isinstance(mixed, RequirementsFile):
            return None
        if isinstance(mixed, Dependency):
            if mixed.url:
                return None
            return mixed.name
        else:
            return mixed

    package_query = [normalized_package for normalized_package in
                     (normalize_dependency_package(p) for p in as_list(mixed)) if normalized_package]
    pip_working_set_init()
    search_packages_results = search_packages_info(package_query)
    return dict(((result['name'].lower(), result['version']) for result in search_packages_results))


def version_satisfies_spec(spec, version):
    if not spec:
        return True
    if not version:
        return False
    if not isinstance(spec, SpecifierSet):
        spec = SpecifierSet(spec)
    if not isinstance(version, Version):
        version = Version(version)
    return spec.contains(version)
