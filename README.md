[PyBuilder](http://pybuilder.github.io) 
=========

[![Build Status](https://secure.travis-ci.org/pybuilder/pybuilder.png?branch=master)](http://travis-ci.org/pybuilder/pybuilder)
[![PyPI version](https://badge.fury.io/py/pybuilder.png)](http://badge.fury.io/py/pybuilder)
[![Coverage Status](https://coveralls.io/repos/pybuilder/pybuilder/badge.png?branch=master)](https://coveralls.io/r/pybuilder/pybuilder?branch=master)

PyBuilder is a software build tool written in 100% pure Python and mainly
targets Python applications.

PyBuilder is based on the concept of dependency based programming but also comes
along with powerful plugin mechanism that allows the construction of build life
cycles similar to those known from other famous (Java) build tools.

PyBuilder is running on the following versions of Python: 2.6, 2.7, 3.2, 3.3 and PyPy.

See the [Travis Build](http://travis-ci.org/#!/pybuilder/pybuilder) for version specific output.

## Installing

PyBuilder is available using pip:

    $ pip install pybuilder

See the [Cheeseshop page](http://pypi.python.org/pypi/pybuilder/) for more
information.

## Getting started

PyBuilder emphasizes simplicity. If you want to build a pure Python project and
use the recommended directory layout, all you have to do is create a file
build.py with the following content:

```python
from pybuilder.core import use_plugin

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.coverage")
use_plugin("python.distutils")

default_task = "publish"
```

See the [PyBuilder homepage](http://pybuilder.github.com/) for more details.

## Plugins

PyBuilder provides a lot of plugins out ot the box that utilize tools and libraries commonly used in Python projects:

* [python.coverage](http://pybuilder.github.com/documentation/plugins.html#measuring_unittest_coverage) - Uses the standard [coverage](http://pypi.python.org/pypi/coverage/) module to calculate unit test line coverage.
* [python.distutils](http://pybuilder.github.com/documentation/plugins.html#building_a_python_egg) - Provides support to generate [setup.py](http://pypi.python.org/pypi/setuptools) files.
* **python.django** - Provides support for developing [Django](https://www.djangoproject.com/) applications.
* [python.flake8](http://pybuilder.github.io/documentation/plugins.html#flake8_plugin) - Provides support for [flake8](http://pypi.python.org/pypi/flake8/)
* [python.pep8](http://pybuilder.github.io/documentation/plugins.html#pep8_plugin) - Provides support for [pep8](http://pypi.python.org/pypi/pep8)
* [python.install_dependencies](http://pybuilder.github.io/documentation/plugins.html#installing_build_and_runtime_dependencies) - Installs the projects build and runtime dependencies using `pip`
* [python.pychecker](http://pybuilder.github.io/documentation/plugins.html#pychecker_plugin) - Provides support for [pychecker](http://pychecker.sourceforge.net/)
* [python.Pydev](http://pybuilder.github.io/documentation/plugins.html#generating_project_files_for_eclipse_pydev) - Generates project files to import projects into [Eclipse PyDev](http://pydev.org/)
* [python.PyCharm](/documentation/plugins.html#ProjectfilesforJetbrainsPyCharm) - Generates project files to import projects into [Jetbrains PyCharm](http://www.jetbrains.com/pycharm/)
* [python.pylint](http://pybuilder.github.io/documentation/plugins.html#pylint_plugin) - Executes [pylint](https://bitbucket.org/logilab/pylint/) on your sources.
* [python.pymetrics](http://pybuilder.github.io/documentation/plugins.html#pymetrics_plugin) - Calculates several metrics using [pymetrics](http://sourceforge.net/projects/pymetrics/)
* [python.unittest](http://pybuilder.github.com/documentation/plugins.html#running_python_unittests) - Executes [unittest](http://docs.python.org/library/unittest.html) test cases
* [python.integrationtest](http://pybuilder.github.com/documentation/plugins.html#running_python_integration_tests) - Executes python scripts as integrations tests

In addition, a few common plugins are provided:

* [copy_resources](http://pybuilder.github.io/documentation/plugins.html#copying_resources_into_a_distribution) - Copies files.
* [filter_resources](http://pybuilder.github.io/documentation/plugins.html#replacing_placeholders_with_actual_values_at_buildtime) - Filters files by replacing tokens with configuration values.
* [source_distribution](http://pybuilder.github.io/documentation/plugins.html#creating_a_source_distribution) - Bundles a source distribution for shipping.

## Release Notes

The release notes can be found [here](http://pybuilder.github.com/releasenotes/)


[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/pybuilder/pybuilder/trend.png)](https://bitdeli.com/free "Bitdeli Badge")

