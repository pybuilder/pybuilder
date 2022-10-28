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

import ast
import logging
import os
import subprocess
import sys
from os.path import pathsep

from pybuilder.install_utils import install_dependencies
from pybuilder.python_utils import is_windows, which
from pybuilder.utils import assert_can_execute, execute_command, jp, np

__all__ = ["PythonEnv", "PythonEnvRegistry"]

_PYTHON_INFO_SCRIPT = """import platform, sys, os, sysconfig
_base_executable = getattr(sys, "_base_executable", None)
_sys_executable = sys.executable
_executable = sys.executable
_platform = sys.platform
if _platform == "linux2":
    _platform = "linux"
print({
"_platform": _platform,
"_os_name": os.name,
"_base_executable": (_base_executable, ),
"_sys_executable": (_sys_executable, ),
"_executable": (_executable, ),
"_exec_dir": os.path.dirname(_executable),
"_name": platform.python_implementation(),
"_type": platform.python_implementation().lower(),
"_version": tuple(sys.version_info),
"_is_pypy": "__pypy__" in sys.builtin_module_names,
"_is_64bit": (getattr(sys, "maxsize", None) or getattr(sys, "maxint")) > 2 ** 32,
"_versioned_dir_name": "%s-%s" % (platform.python_implementation().lower(), ".".join(str(f) for f in sys.version_info)),
"_environ": dict(os.environ),
"_darwin_python_framework": sysconfig.get_config_var("PYTHONFRAMEWORK")
})
"""

_FIELDS = {"platform", "executable", "name", "type", "version", "env_dir", "versioned_dir_name", "os_name",
           "site_paths", "is_pypy", "is_64bit", "environ", "exec_dir"}


class PythonEnv(object):
    def __init__(self, env_dir, reactor, platform=None, install_log_name="install.log"):
        self._env_dir = env_dir
        self._reactor = reactor
        self._platform = platform or sys.platform
        self._long_desc = "Unpopulated"
        self._site_paths = None
        self._venv_symlinks = os.name == "posix"
        self._install_log_path = jp(self._env_dir, install_log_name)
        self._populated = False

    def _check_populated(self):
        if self._populated:
            raise RuntimeError("already populated")

    def _check_not_populated(self):
        if not self._populated:
            raise RuntimeError("not yet populated")

    def populate(self):
        """Populates the environment information from the real Python"""
        self._check_populated()

        python_exec_path = _venv_python_executable(self._env_dir, self._platform)
        result = subprocess.check_output([python_exec_path, "-c", _PYTHON_INFO_SCRIPT], universal_newlines=True)
        python_info = ast.literal_eval(result)

        for k, v in python_info.items():
            setattr(self, k, v)

        # Python data is all uploaded
        self._populated = True

        self._recalculate_derived()
        return self

    def _recalculate_derived(self):
        self._site_paths = tuple(self._get_site_paths())

        environ_path = self._environ.get("PATH")
        if environ_path:
            self._environ["PATH"] = pathsep.join([self._exec_dir] + environ_path.split(pathsep))

        self._long_desc = "%s version %s on %s in %s" % (self.name,
                                                         ".".join(str(v) for v in self.version),
                                                         self.platform,
                                                         self.executable)
        self._short_desc = "%s %s" % (self.name, ".".join(str(v) for v in self.version))

    def __str__(self):
        return self._long_desc

    @property
    def venv_symlinks(self):
        return self._venv_symlinks

    @property
    def reactor(self):
        return self._reactor

    @property
    def project(self):
        return self._reactor.project

    @property
    def logger(self):
        return self._reactor.logger

    @property
    def install_log_path(self):
        return self._install_log_path

    @property
    def platform(self):
        self._check_not_populated()
        return self._platform

    @property
    def executable(self):
        self._check_not_populated()
        return list(self._executable)

    @property
    def name(self):
        self._check_not_populated()
        return self._name

    @property
    def type(self):
        self._check_not_populated()
        return self._type

    @property
    def version(self):
        self._check_not_populated()
        return self._version

    @property
    def env_dir(self):
        return self._env_dir

    @property
    def exec_dir(self):
        return self._exec_dir

    @property
    def versioned_dir_name(self):
        self._check_not_populated()
        return self._versioned_dir_name

    @property
    def os_name(self):
        self._check_not_populated()
        return self._os_name

    @property
    def site_paths(self):
        self._check_not_populated()
        return list(self._site_paths)

    @property
    def is_pypy(self):
        self._check_not_populated()
        return self._is_pypy

    @property
    def is_64bit(self):
        self._check_not_populated()
        return self._is_64bit

    @property
    def environ(self):
        self._check_not_populated()
        return dict(self._environ)

    def overwrite(self, prop, value):
        if prop not in _FIELDS:
            raise KeyError("'%s' is not a property that can be overwritten" % prop)
        setattr(self, "_%s" % prop, value)

        self._recalculate_derived()

    def create_venv(self, system_site_packages=False,
                    clear=False,
                    symlinks=False,
                    upgrade=False,
                    with_pip=False,
                    prompt=None,
                    offline=False,
                    ):
        """Creates VEnv in the designated location. Must not be yet populated."""

        self._check_populated()

        create_venv(self._env_dir,
                    system_site_packages=system_site_packages,
                    clear=clear,
                    symlinks=symlinks,
                    upgrade=upgrade,
                    with_pip=with_pip,
                    prompt=prompt,
                    offline=offline,
                    logger=self.logger)

        return self.populate()

    def recreate_venv(self, system_site_packages=False,
                      clear=False,
                      symlinks=False,
                      upgrade=False,
                      with_pip=False,
                      prompt=None,
                      offline=False,
                      ):

        create_venv(self._env_dir,
                    system_site_packages=system_site_packages,
                    clear=clear,
                    symlinks=symlinks,
                    upgrade=upgrade,
                    with_pip=with_pip,
                    prompt=prompt,
                    offline=offline,
                    logger=self.logger)

        return self

    def install_dependencies(self, pip_batch,
                             install_log_path=None,
                             local_mapping=None,
                             constraints_file_name=None,
                             log_file_mode="ab",
                             package_type="dependency",
                             target_dir=None,
                             ignore_installed=False,
                             ):

        install_dependencies(self.logger, self.project,
                             pip_batch,
                             self,
                             install_log_path or self.install_log_path,
                             local_mapping=local_mapping,
                             constraints_file_name=constraints_file_name,
                             log_file_mode=log_file_mode,
                             package_type=package_type,
                             target_dir=target_dir,
                             ignore_installed=ignore_installed)

    def verify_can_execute(self, command_and_arguments, prerequisite, caller, env=None, no_path_search=False,
                           inherit_env=True):
        environ = self.environ if inherit_env else {}
        if env:
            environ.update(env)
        return assert_can_execute(command_and_arguments, prerequisite, caller, env=environ,
                                  no_path_search=no_path_search, logger=self.logger)

    def execute_command(self, command_and_arguments,
                        outfile_name=None,
                        env=None,
                        cwd=None,
                        error_file_name=None,
                        shell=False,
                        no_path_search=False,
                        inherit_env=True):
        environ = self.environ if inherit_env else {}
        if env:
            environ.update(env)

        return execute_command(command_and_arguments, outfile_name=outfile_name, env=environ, cwd=cwd,
                               error_file_name=error_file_name, shell=shell, no_path_search=no_path_search,
                               logger=self.logger)

    def run_process_and_wait(self, commands, cwd, stdout, stderr=None, no_path_search=True):
        if is_windows(self.platform) and not no_path_search:
            which_cmd = which(commands[0], path=self.environ.get("PATH"))
            if which_cmd:
                commands[0] = which_cmd

        with open(os.devnull) as devnull:
            process = subprocess.Popen(commands,
                                       cwd=cwd,
                                       stdin=devnull,
                                       stdout=stdout,
                                       stderr=stderr or stdout,
                                       shell=False)
            return process.wait()

    def _get_site_paths(self):
        prefix = self.env_dir
        if self.is_pypy:
            yield os.path.join(prefix, "lib", "pypy%d.%d" % self.version[:2], "site-packages")
            yield os.path.join(prefix, "site-packages")
        elif os.sep == "/":
            yield os.path.join(prefix, "lib",
                               "python%d.%d" % self.version[:2],
                               "site-packages")
        else:
            yield prefix
            yield os.path.join(prefix, "lib", "site-packages")

        if self.platform == "darwin":
            # for framework builds *only* we add the standard Apple
            # locations.
            framework = self._darwin_python_framework
            if framework:
                yield os.path.join("/Library", framework,
                                   "%d.%d" % self.version[:2], "site-packages")


class PythonEnvRegistry(object):
    def __init__(self, reactor):
        self.reactor = reactor
        self.logger = reactor.logger
        self._registry = {}

    def __setitem__(self, key, value):
        """type: (str, PythonEnv) -> None"""
        registry = self._registry
        existing_env = registry.get(key)
        if existing_env:
            raise KeyError("environment '%s' is already registered: %s", key, existing_env[-1])

        self.logger.debug("Registered Python environment '%s': %s", key, value)
        existing_env = [value]
        registry[key] = existing_env

    def __delitem__(self, key):
        """type: (str) -> None"""
        return self._registry.__delitem__(key)

    def __getitem__(self, item):
        """type: (str) -> PythonEnv"""
        registry = self._registry
        existing_env = registry.get(item)
        if not existing_env:
            raise KeyError("no environment '%s' registered" % item)
        return self._registry[item][-1]

    def push_override(self, key, value):
        registry = self._registry
        existing_env = registry.get(key)
        if not existing_env:
            raise KeyError("no environment '%s' registered" % key)

        existing_env.append(value)

    def pop_override(self, key):
        registry = self._registry
        existing_env = registry.get(key)

        if not existing_env:
            raise KeyError("no environment '%s' registered" % key)

        if len(existing_env) == 1:
            raise RuntimeError("environment '%s' is not overridden" % key)

        del existing_env[-1]


def create_venv(home_dir,
                system_site_packages=False,
                clear=False,
                symlinks=False,
                upgrade=False,
                with_pip=False,
                prompt=None,
                offline=False,
                logger=None):
    import virtualenv

    args = [home_dir, "--no-periodic-update", "-p", sys.executable]

    if upgrade and (not offline):
        pass
    #        args_upgrade = list(args)
    #        args_upgrade.append("--download")
    #        args_upgrade.append("--upgrade-embed-wheels")
    #        try:
    #            virtualenv.cli_run(args_upgrade, setup_logging=False)
    #        except SystemExit as e:
    #            if e.code:
    #                raise RuntimeError("VirtualEnv upgrade has not completed successfully", e)

    if clear:
        args.append("--clear")

    # if logger.level < logger.WARNING:
    #    args += ["-v"]

    if symlinks:
        args.append("--symlinks")
    else:
        args.append("--copies")
    if not with_pip:
        args.append("--no-pip")
    if system_site_packages:
        args.append("--system-site-packages")
    if prompt:
        args += ["--prompt", prompt]

    logging.getLogger("filelock").setLevel(logging.INFO)
    virtualenv.cli_run(args, setup_logging=False)


_, _venv_python_exename = os.path.split(os.path.abspath(getattr(sys, "_base_executable", sys.executable)))
venv_symlinks = os.name == "posix"

# On Windows python.exe could be in PythonXY/ or venv/Scripts/
# python[3[.x]].exe may also not be available, only python.exe
_windows_exec_candidates = (lambda env_dir: jp(env_dir, "Scripts", _venv_python_exename),
                            lambda env_dir: jp(env_dir, _venv_python_exename),
                            lambda env_dir: jp(env_dir, "Scripts", "python.exe"),
                            lambda env_dir: jp(env_dir, "python.exe"),
                            )


def _venv_python_executable(env_dir, platform):
    """Binary Python executable for a specific virtual environment"""
    if is_windows(platform):
        for candidate_func in _windows_exec_candidates:
            candidate = candidate_func(env_dir)
            if os.path.exists(candidate):
                break
    else:
        candidate = jp(env_dir, "bin", _venv_python_exename)

    return np(candidate)
