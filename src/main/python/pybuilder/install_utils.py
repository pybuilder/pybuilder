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

from pybuilder.core import RequirementsFile, Dependency
from pybuilder.errors import BuildFailedException
from pybuilder.pip_utils import (create_constraint_file,
                                 pip_install_batches,
                                 should_update_package,
                                 version_satisfies_spec,
                                 as_pip_install_target,
                                 get_packages_info)
from pybuilder.utils import as_list, tail_log, np, jp


def install_dependencies(logger, project, dependencies, python_env,
                         log_file_name,
                         local_mapping=None,
                         constraints_file_name=None,
                         log_file_mode="ab",
                         package_type="dependency",
                         target_dir=None,
                         ignore_installed=False,
                         ):
    entry_paths = target_dir or python_env.site_paths
    dependencies_to_install, orig_installed_pkgs, dependency_constraints = _filter_dependencies(logger,
                                                                                                project,
                                                                                                dependencies,
                                                                                                entry_paths,
                                                                                                ignore_installed)
    constraints_file = None
    if constraints_file_name:
        constraints_file = np(jp(python_env.env_dir, constraints_file_name))
        create_constraint_file(constraints_file, dependency_constraints)

    if not local_mapping:
        local_mapping = {}

    install_batch = []
    for dependency in dependencies_to_install:
        url = getattr(dependency, "url", None)
        install_options = {}

        if should_update_package(dependency.version) and not getattr(dependency, "version_not_a_spec", False):
            install_options["upgrade"] = True

        if dependency.name in local_mapping or url:
            install_options["force_reinstall"] = bool(url)

        if not target_dir and dependency.name in local_mapping:
            install_options["target_dir"] = local_mapping[dependency.name]

        install_batch.append((as_pip_install_target(dependency), install_options))

        logger.info("Processing %s packages '%s%s'%s to be installed with %s", package_type, dependency.name,
                    dependency.version if dependency.version else "",
                    " from %s" % url if url else "", install_options)

    if install_batch:
        pip_env = {"PIP_NO_INPUT": "1"}

        if project.offline:
            pip_env["PIP_NO_INDEX"] = "1"
            logger.warn("PIP will be operating in the offline mode")

        with open(np(log_file_name), log_file_mode) as log_file:
            for result in pip_install_batches(install_batch,
                                              python_env,
                                              index_url=project.get_property("install_dependencies_index_url"),
                                              extra_index_url=project.get_property(
                                                  "install_dependencies_extra_index_url"),
                                              trusted_host=project.get_property("install_dependencies_trusted_host"),
                                              insecure_installs=project.get_property(
                                                  "install_dependencies_insecure_installation"),
                                              verbose=project.get_property("pip_verbose"),
                                              constraint_file=constraints_file,
                                              logger=logger,
                                              outfile_name=log_file,
                                              error_file_name=log_file,
                                              target_dir=target_dir,
                                              ignore_installed=ignore_installed):
                if result:
                    try:
                        log_file.close()
                    finally:
                        raise BuildFailedException("Unable to install %s packages into %s. "
                                                   "Please see '%s' for full details:\n%s",
                                                   package_type,
                                                   python_env.env_dir,
                                                   log_file_name,
                                                   tail_log(log_file_name))
    return dependencies_to_install


def _filter_dependencies(logger, project, dependencies, entry_paths, ignore_installed):
    dependencies = as_list(dependencies)
    installed_packages = get_packages_info(entry_paths)
    dependencies_to_install = []
    dependency_constraints = []

    for dependency in dependencies:
        logger.debug("Inspecting package %s", dependency)
        if ignore_installed:
            logger.debug("Package %s will be installed because existing installation will be ignored", dependency)
            dependencies_to_install.append(dependency)
            continue

        if dependency.declaration_only:
            logger.info("Package %s is declaration-only and will not be installed", dependency)
            continue

        if isinstance(dependency, RequirementsFile):
            # Always add requirement file-based dependencies
            logger.debug("Package %s is a requirement file and will be updated", dependency)
            dependencies_to_install.append(dependency)
            continue

        elif isinstance(dependency, Dependency):
            if dependency.version:
                dependency_constraints.append(dependency)
                logger.debug("Package %s is added to the list of installation constraints", dependency)

            if dependency.url:
                # Always add dependency that is url-based
                logger.debug("Package %s is URL-based and will be updated", dependency)
                dependencies_to_install.append(dependency)
                continue

            if should_update_package(dependency.version) and not getattr(dependency, "version_not_a_spec", False):
                # Always add dependency that has a version specifier indicating desire to always update
                logger.debug("Package %s has a non-exact version specifier and will be updated", dependency)
                dependencies_to_install.append(dependency)
                continue

        dependency_name = dependency.name.lower()
        if dependency_name not in installed_packages:
            # If dependency not installed at all then install it
            logger.debug("Package %s is not installed and will be installed", dependency)
            dependencies_to_install.append(dependency)
            continue

        if dependency.version and not version_satisfies_spec(dependency.version,
                                                             installed_packages[dependency_name].version):
            # If version is specified and version constraint is not satisfied
            logger.debug("Package '%s' is not satisfied by installed dependency version '%s' and will be installed" %
                         (dependency, installed_packages[dependency_name].version))
            dependencies_to_install.append(dependency)
            continue

        logger.debug("Package '%s' is already up-to-date and will be skipped" % dependency)

    return dependencies_to_install, installed_packages, dependency_constraints
