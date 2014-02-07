#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0(the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
    The PyBuilder testutils module.
    Provides generic test utilities that can be used to write shorter tests.
"""

import pip


def assert_is_not_locally_installed(package_name):
    """
        Ensure that a package is not locally installed. This is useful to detect
        when the package you are testing from sources is also installed in your
        environment.
        Tests usually expect to have a package in the same version, but if the
        package is installed locally then the package version is the installed version
        and not the same as the tests.
    """
    installed_packages = pip.get_installed_distributions()
    for installed_package in installed_packages:
        if package_name == installed_package.project_name:
            message = ('Package {0} is installed locally (version {1}). ' +
                       'This will lead to problems while developing.')
            raise AssertionError(message.format(
                                 installed_package.project_name, installed_package.version))
