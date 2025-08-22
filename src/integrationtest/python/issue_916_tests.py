#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2024 PyBuilder Team
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

import textwrap
import unittest
from os.path import relpath

from smoke_itest_support import SmokeIntegrationTestSupport


class Issue916Test(SmokeIntegrationTestSupport):
    def test(self):
        self.write_file("pyproject.toml", textwrap.dedent(
            """
            [build-system]
            requires = []
            build-backend = "pybuilder.pep517"
            backend-path = ["src/main/python"]
            """
        ))
        self.write_build_file(textwrap.dedent(
            """
            # -*- coding: utf-8 -*-
            #
            # (C) Copyright 2021 Karellen, Inc. (https://www.karellen.co/)
            #
            # Licensed under the Apache License, Version 2.0 (the "License");
            # you may not use this file except in compliance with the License.
            # You may obtain a copy of the License at
            #
            #     http://www.apache.org/licenses/LICENSE-2.0
            #
            # Unless required by applicable law or agreed to in writing, software
            # distributed under the License is distributed on an "AS IS" BASIS,
            # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
            # See the License for the specific language governing permissions and
            # limitations under the License.
            #

            from os import environ
            from pybuilder.core import (use_plugin, init, Author, task, depends, dependents)

            use_plugin("python.install_dependencies")
            use_plugin("python.core")
            use_plugin("python.distutils")

            name = "wheel_axle"
            version = "0.0.9.dev"

            summary = "Axle is Python wheel enhancement library"
            authors = [Author("Karellen, Inc.", "supervisor@karellen.co")]
            maintainers = [Author("Arcadiy Ivanov", "arcadiy@karellen.co")]
            url = "https://github.com/karellen/wheel-axle"
            urls = {
                "Bug Tracker": "https://github.com/karellen/wheel-axle/issues",
                "Source Code": "https://github.com/karellen/wheel-axle/",
                "Documentation": "https://github.com/karellen/wheel-axle/"
            }
            license = "Apache-2.0"

            requires_python = ">=3.9"

            default_task = ["analyze", "publish"]

            @task
            @depends("install_dependencies")
            @dependents("compile_sources")
            def install_ci_dependencies(project):
                pass


            @init
            def set_properties(project):
                project.set_property("distutils_readme_description", True)
                project.set_property("distutils_description_overwrite", True)
                project.set_property("distutils_upload_skip_existing", True)
                project.set_property("distutils_setup_keywords", ["wheel", "packaging",
                                                                  "setuptools", "bdist_wheel",
                                                                  "symlink", "postinstall"])

                project.set_property("distutils_classifiers", [
                    "License :: OSI Approved :: Apache Software License",
                    "Programming Language :: Python :: 3.7",
                    "Programming Language :: Python :: 3.8",
                    "Programming Language :: Python :: 3.9",
                    "Programming Language :: Python :: 3.10",
                    "Programming Language :: Python :: 3.11",
                    "Programming Language :: Python :: 3.12",
                    "Programming Language :: Python :: 3.13",
                    "Operating System :: MacOS :: MacOS X",
                    "Operating System :: POSIX",
                    "Operating System :: POSIX :: Linux",
                    "Topic :: System :: Archiving :: Packaging",
                    "Topic :: Software Development :: Build Tools",
                    "Intended Audience :: Developers",
                    "Development Status :: 4 - Beta"
                ])
            """))

        self.smoke_test_module("pip", "-vvvvvvvvvvvvvv", "install", ".")


if __name__ == "__main__":
    unittest.main()
