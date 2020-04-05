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

from __future__ import unicode_literals

import os
import shutil


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    def artifact_filter(artifact_name):
        return artifact_name.lower().endswith(".whl")

    return build_with_pyb(wheel_directory, "Wheel", artifact_filter, config_settings, metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    def artifact_filter(artifact_name):
        return artifact_name.lower().endswith(".tar.gz")

    return build_with_pyb(sdist_directory, "SDist", artifact_filter, config_settings)


def build_with_pyb(target_dir, artifact_name, artifact_filter, config_settings=None, metadata_directory=None):
    from pybuilder.cli import main
    # verbose, debug, skip all optional...
    if main("-v", "-X", "-o", "--reset-plugins", "clean", "publish"):
        raise RuntimeError("PyBuilder build failed")

    from pybuilder.reactor import Reactor
    from pybuilder.plugins.python.distutils_plugin import _get_generated_artifacts
    reactor = Reactor.current_instance()
    project = reactor.project
    logger = reactor.logger
    dist_dir, artifacts = _get_generated_artifacts(project, logger)

    filtered = list(filter(artifact_filter, artifacts))
    if len(filtered) > 1:
        raise RuntimeError("Multiple project %ss found, don't know which to install: %r" % (artifact_name, filtered,))
    if not filtered:
        raise RuntimeError("Project did not generate any %ss install: %r" % (artifact_name, artifacts,))
    artifact = filtered[0]
    shutil.copy2(artifact, target_dir)

    return os.path.basename(artifact)
