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

from pybuilder.core import RequirementsFile, Dependency, _dependency_spec
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
                                                                                                python_env,
                                                                                                entry_paths,
                                                                                                ignore_installed,
                                                                                                package_type)
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

        eager_update = getattr(dependency, "eager_update", None)
        version_not_a_spec = getattr(dependency, "version_not_a_spec", False)
        if eager_update or (eager_update is None and should_update_package(dependency.version) and
                            not version_not_a_spec):
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


def _conflict_origin(dependency, package_type):
    """How to name a dependency in a conflict message.

    At install time the buckets have already been merged, so `package_type` - "dependency",
    "plugin" or "vendorized" - is all that is known about anything outside an extras group.
    """
    extra = getattr(dependency, "extra", None)
    return package_type if extra is None else "extra '%s' dependency" % extra


def _resolve_dependencies(logger, dependencies, marker_env, package_type):
    """Reduce the union of build, runtime and selected-extras dependencies to the set that applies
    to the target environment.

    pip merges identical constraint lines and drops lines whose markers do not hold, but intersects
    everything else, so two live entries for one distribution become a ResolutionImpossible that
    names neither origin. Deciding it here means the build can say which declarations disagree.
    """
    from pybuilder import pip_common

    applicable = []
    candidates_by_name = {}
    for dependency in dependencies:
        markers = getattr(dependency, "markers", None)
        if not pip_common.markers_apply(markers, marker_env, getattr(dependency, "extra", None)):
            logger.debug("Package %s does not apply to this environment and will be skipped", dependency)
            continue
        if dependency in applicable:
            logger.debug("Package %s is declared more than once identically and will be installed once", dependency)
            continue
        applicable.append(dependency)

        if isinstance(dependency, Dependency):
            candidates_by_name.setdefault(pip_common.canonicalize_name(dependency.name), []).append(dependency)

    for candidates in candidates_by_name.values():
        for index, left in enumerate(candidates):
            for right in candidates[index + 1:]:
                if pip_common.specifiers_conflict(left.version, right.version):
                    left_origin = _conflict_origin(left, package_type)
                    raise BuildFailedException("%s '%s' conflicts with %s '%s' in this environment",
                                               left_origin[0].upper() + left_origin[1:], _dependency_spec(left),
                                               _conflict_origin(right, package_type), _dependency_spec(right))

    return applicable


def _unsatisfied_extras(logger, dependency, installed_packages):
    """Distributions required by the dependency's extras that are not installed.

    Nothing in installed metadata records which extras were requested, so whether `foo[security]`
    was ever really installed can only be answered by resolving what `security` requires from foo's
    own metadata and looking for those. Returns None when even that cannot answer it.
    """
    from pybuilder import pip_common

    package = installed_packages[pip_common.canonicalize_name(dependency.name)]
    unsatisfied = []
    for extra in dependency.extras:
        extra_name = pip_common.safe_extra(extra)
        if extra_name not in package.extra_requires:
            logger.warn("Package '%s' does not provide extra '%s' and cannot be verified as installed; "
                        "it will be handed to pip", dependency.name, extra)
            return None
        unsatisfied.extend(required for required in package.extra_requires[extra_name]
                           if required not in installed_packages)

    return unsatisfied


def _filter_dependencies(logger, project, dependencies, python_env, entry_paths, ignore_installed,
                         package_type="dependency"):
    marker_env = python_env.marker_env
    dependencies = _resolve_dependencies(logger, as_list(dependencies), marker_env, package_type)
    installed_packages = get_packages_info(entry_paths, marker_env=marker_env)
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

        if getattr(dependency, "extras", None):
            unsatisfied = _unsatisfied_extras(logger, dependency, installed_packages)
            if unsatisfied is None:
                dependencies_to_install.append(dependency)
                continue
            if unsatisfied:
                logger.debug("Package '%s' is installed but its extras still require %s, "
                             "so it will be installed", dependency, ", ".join(sorted(unsatisfied)))
                dependencies_to_install.append(dependency)
                continue

        logger.debug("Package '%s' is already up-to-date and will be skipped" % dependency)

    return dependencies_to_install, installed_packages, dependency_constraints
