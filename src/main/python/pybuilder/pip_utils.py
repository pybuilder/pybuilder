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

from pybuilder.core import Dependency, RequirementsFile
from pybuilder.utils import execute_command, as_list
# Plugin install_dependencies_plugin can reload pip_common and pip_utils. Do not use from ... import ...
from pybuilder import pip_common

PIP_EXEC_STANZA = [sys.executable, "-m", "pip.__main__"]
__RE_PIP_PACKAGE_VERSION = re.compile(r"^Version:\s+(.+)$", re.MULTILINE)


def build_dependency_version_string(mixed):
    if isinstance(mixed, Dependency):
        version = mixed.version
    else:
        version = mixed

    if not version:
        return ""

    return version


def pip_install(install_targets, index_url=None, extra_index_url=None, upgrade=False, insecure_installs=None,
                force_reinstall=False, target_dir=None, verbose=False, trusted_host=None, constraint_file=None,
                eager_upgrade=False,
                logger=None, outfile_name=None, error_file_name=None, env=None, cwd=None):
    pip_command_line = list()
    pip_command_line.extend(PIP_EXEC_STANZA)
    pip_command_line.append("install")
    pip_command_line.extend(build_pip_install_options(index_url=index_url,
                                                      extra_index_url=extra_index_url,
                                                      upgrade=upgrade,
                                                      insecure_installs=insecure_installs,
                                                      force_reinstall=force_reinstall,
                                                      target_dir=target_dir,
                                                      verbose=verbose,
                                                      trusted_host=trusted_host,
                                                      constraint_file=constraint_file,
                                                      eager_upgrade=eager_upgrade
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
                              force_reinstall=False, target_dir=None, verbose=False, trusted_host=None,
                              constraint_file=None, eager_upgrade=False):
    options = []
    if index_url:
        options.append("--index-url")
        options.append(index_url)

    if extra_index_url:
        extra_index_urls = as_list(extra_index_url)
        for url in extra_index_urls:
            options.append("--extra-index-url")
            options.append(url)

    if trusted_host:
        trusted_hosts = as_list(trusted_host)
        for host in trusted_hosts:
            options.append("--trusted-host")
            options.append(host)

    if upgrade:
        options.append("--upgrade")
        if pip_common.pip_version >= "9.0":
            options.append("--upgrade-strategy")
            if eager_upgrade:
                options.append("eager")
            else:
                options.append("only-if-needed")

    if verbose:
        options.append("--verbose")

    if force_reinstall:
        options.append("--force-reinstall")

    if target_dir:
        options.append("-t")
        options.append(target_dir)

    if constraint_file and pip_common._pip_supports_constraints():
        options.append("-c")
        options.append(constraint_file)

    if pip_common._pip_disallows_insecure_packages_by_default() and insecure_installs:
        for insecure_install in insecure_installs:
            arguments_for_insecure_installation = ["--allow-unverified", insecure_install,
                                                   "--allow-external", insecure_install]
            options.extend(arguments_for_insecure_installation)

    return options


def create_constraint_file(file_name, constraints):
    with open(file_name, "wt") as fout:
        for constraint in as_pip_install_target(constraints):
            fout.write("%s\n" % constraint)


def as_pip_install_target(mixed):
    arguments = []
    targets = as_list(mixed)

    for target in targets:
        if isinstance(target, RequirementsFile):
            arguments.extend(("-r", target.name))
        elif isinstance(target, Dependency):
            if target.url:
                arguments.append(target.url)
            else:
                arguments.append("{0}{1}".format(target.name, build_dependency_version_string(target)))
        else:
            arguments.append(str(target))

    return arguments


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
    pip_common.pip_working_set_init()
    search_packages_results = pip_common.search_packages_info(package_query)
    return dict(((result['name'].lower(), result['version']) for result in search_packages_results))


def version_satisfies_spec(spec, version):
    if not spec:
        return True
    if not version:
        return False
    if not isinstance(spec, pip_common.SpecifierSet):
        spec = pip_common.SpecifierSet(spec)
    if not isinstance(version, pip_common.Version):
        version = pip_common.Version(version)
    return spec.contains(version)


def should_update_package(version):
    """
        True if the version is specified and isn't exact
        False otherwise
    """
    if version:
        if not isinstance(version, pip_common.SpecifierSet):
            version_specifier = pip_common.SpecifierSet(version)
        else:
            version_specifier = version
        # We always check if even one specifier in the set is not exact
        for spec in version_specifier._specs:
            if hasattr(spec, "operator"):
                if spec.operator not in ("==", "==="):
                    return True
            else:
                if spec._spec[0] not in ("==", "==="):
                    return True

    return False
