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

from collections import namedtuple

from pybuilder.core import Dependency, RequirementsFile
from pybuilder.pip_common import canonicalize_name, WorkingSet, SpecifierSet, Version
from pybuilder.python_utils import odict
from pybuilder.utils import as_list

PIP_MODULE_STANZA = ["-m", "pip.__main__"]


def build_dependency_version_string(mixed):
    if isinstance(mixed, Dependency):
        version = mixed.version
    else:
        version = mixed

    if not version:
        return ""

    return version


def pip_install_batches(packages, python_env, index_url=None, extra_index_url=None, upgrade=False,
                        insecure_installs=None,
                        force_reinstall=False, target_dir=None, verbose=False, trusted_host=None, constraint_file=None,
                        eager_upgrade=False, ignore_installed=False, prefix_dir=None,
                        logger=None, outfile_name=None, error_file_name=None, env=None, cwd=None):
    """install_batches is a list of dependencies in a form of a tuple [package_spec, {build options}}]
    The batches will be assembled in a way that ensures that installation of packages with identical options occurs
    together to cut down on the number of round trips.
    """
    pip_command_line = []
    pip_command_line.extend(python_env.executable + PIP_MODULE_STANZA)
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
                                                      eager_upgrade=eager_upgrade,
                                                      ignore_installed=ignore_installed,
                                                      prefix_dir=prefix_dir,
                                                      ))
    env_environ = python_env.environ
    if env is not None:
        env_environ.update(env)

    batches = odict()
    for package in packages:
        pkg_spec, opts = package
        opts = tuple(build_pip_install_options(**opts))

        if opts in batches:
            batch_pkgs = batches[opts]
        else:
            batch_pkgs = []
            batches[opts] = batch_pkgs
        batch_pkgs.append(pkg_spec)

    for opts, pkgs in batches.items():
        cmd_line = list(pip_command_line)
        cmd_line.extend(opts)
        for pkg in pkgs:
            cmd_line.extend(pkg)

        yield python_env.execute_command(cmd_line,
                                         outfile_name=outfile_name,
                                         error_file_name=error_file_name,
                                         env=env_environ,
                                         cwd=cwd,
                                         shell=False,
                                         no_path_search=True)


def pip_install(install_targets, python_env, index_url=None, extra_index_url=None, upgrade=False,
                insecure_installs=None,
                force_reinstall=False, target_dir=None, verbose=False, trusted_host=None, constraint_file=None,
                eager_upgrade=False, ignore_installed=False, prefix_dir=None,
                logger=None, outfile_name=None, error_file_name=None, env=None, cwd=None):
    pip_command_line = list()
    pip_command_line.extend(python_env.executable + PIP_MODULE_STANZA)
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
                                                      eager_upgrade=eager_upgrade,
                                                      ignore_installed=ignore_installed,
                                                      prefix_dir=prefix_dir,
                                                      ))
    for install_target in as_list(install_targets):
        pip_command_line.extend(as_pip_install_target(install_target))

    env_environ = python_env.environ
    if env is not None:
        env_environ.update(env)

    if logger:
        logger.debug("Invoking PIP: '%s'", _log_cmd_line(*pip_command_line))

    return python_env.execute_command(pip_command_line,
                                      outfile_name=outfile_name,
                                      error_file_name=error_file_name,
                                      env=env_environ,
                                      cwd=cwd,
                                      shell=False,
                                      no_path_search=True)


def build_pip_install_options(index_url=None, extra_index_url=None, upgrade=False, insecure_installs=None,
                              force_reinstall=False, target_dir=None, verbose=False, trusted_host=None,
                              constraint_file=None, eager_upgrade=False, ignore_installed=False, prefix_dir=None):
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
        options.append("--upgrade-strategy")
        if eager_upgrade:
            options.append("eager")
        else:
            options.append("only-if-needed")

    if verbose:
        verbose = int(verbose)
        if verbose > 3:
            verbose = 3
        options.append("-" + ("v" * verbose))

    if force_reinstall:
        options.append("--force-reinstall")

    if target_dir:
        options.append("-t")
        options.append(target_dir)

    if ignore_installed:
        options.append("-I")

    if prefix_dir:
        options.append("--prefix")
        options.append(prefix_dir)

    if constraint_file:
        options.append("-c")
        options.append(constraint_file)

    if insecure_installs:
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


def get_package_version(mixed, logger=None, entry_paths=None):
    def normalize_dependency_package(mixed):
        if isinstance(mixed, RequirementsFile):
            return None
        if isinstance(mixed, Dependency):
            if mixed.url:
                return None
            return mixed.name
        else:
            return mixed

    entry_paths = as_list(entry_paths) if entry_paths is not None else None
    package_query = [normalized_package for normalized_package in
                     (normalize_dependency_package(p) for p in as_list(mixed)) if normalized_package]
    ws = WorkingSet(entry_paths)
    search_packages_results = list(search_packages_info(package_query, ws))
    return {result['name'].lower(): result['version'] for result in search_packages_results}


_PackageInfo = namedtuple("PackageInfo", ["name", "version", "location", "requires"])


def get_packages_info(entry_paths=None):
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files.
    """
    entry_paths = as_list(entry_paths) if entry_paths is not None else None
    ws = WorkingSet(entry_paths)
    installed = {}
    for dist in ws:
        package = _PackageInfo(canonicalize_name(dist.project_name),
                               dist.version,
                               dist.location,
                               [dep.project_name for dep in dist.requires()])

        installed[package.name] = package

    return installed


def search_packages_info(query, ws):
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files.
    """
    installed = {}
    for p in ws:
        installed[canonicalize_name(p.project_name)] = p

    query_names = [canonicalize_name(name) for name in query]

    for dist in [installed[pkg] for pkg in query_names if pkg in installed]:
        package = {
            'name': dist.project_name,
            'version': dist.version,
            'location': dist.location,
            'requires': [dep.project_name for dep in dist.requires()],
        }

        yield package


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


def should_update_package(version):
    """
        True if the version is specified and isn't exact
        False otherwise
    """
    if version:
        if not isinstance(version, SpecifierSet):
            version_specifier = SpecifierSet(version)
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


def _log_cmd_line(*args):
    result = ""
    first = False
    for arg in args:
        result += first * " " + '"%s"' % arg
        first = True
    return result
