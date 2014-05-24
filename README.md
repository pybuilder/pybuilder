[PyBuilder](http://pybuilder.github.io) 
=========

[![Build Status](https://secure.travis-ci.org/pybuilder/pybuilder.png?branch=master)](http://travis-ci.org/pybuilder/pybuilder)
[![PyPI version](https://badge.fury.io/py/pybuilder.png)](http://badge.fury.io/py/pybuilder)
[![Coverage Status](https://coveralls.io/repos/pybuilder/pybuilder/badge.png?branch=master)](https://coveralls.io/r/pybuilder/pybuilder?branch=master)
[![Ready in backlog](https://badge.waffle.io/pybuilder/pybuilder.png?label=ready&title=Ready)](https://waffle.io/pybuilder/pybuilder)
[![Open bugs](https://badge.waffle.io/pybuilder/pybuilder.png?label=bug&title=Open%20Bugs)](https://waffle.io/pybuilder/pybuilder)


PyBuilder is a software build tool written in 100% pure Python and mainly
targets Python applications.

PyBuilder is based on the concept of dependency based programming but also comes
along with powerful plugin mechanism that allows the construction of build life
cycles similar to those known from other famous (Java) build tools.

PyBuilder is running on the following versions of Python: 2.6, 2.7, 3.2, 3.3, 3.4 and PyPy.

See the [Travis Build](https://travis-ci.org/pybuilder/pybuilder) for version specific output.

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

* [python.coverage](http://pybuilder.github.com/documentation/plugins.html#Measuringunittestcoverage) - Uses the standard [coverage](http://pypi.python.org/pypi/coverage/) module to calculate unit test line coverage.
* [python.distutils](http://pybuilder.github.com/documentation/plugins.html#BuildingaPythonpackage) - Provides support to generate and use [setup.py](http://pypi.python.org/pypi/setuptools) files.
* **python.django** - Provides support for developing [Django](https://www.djangoproject.com/) applications.
* [python.frosted](http://pybuilder.github.io/documentation/plugins.html#Frostedplugin) - Lint source files with [frosted](https://github.com/timothycrosley/frosted)
* [python.flake8](http://pybuilder.github.io/documentation/plugins.html#Flake8plugin) - Provides support for [flake8](http://pypi.python.org/pypi/flake8/)
* [python.pep8](http://pybuilder.github.io/documentation/plugins.html#Pep8plugin) - Provides support for [pep8](http://pypi.python.org/pypi/pep8)
* [python.install_dependencies](http://pybuilder.github.io/documentation/plugins.html#Installingdependencies) - Installs the projects build and runtime dependencies using `pip`
* [python.pychecker](http://pybuilder.github.io/documentation/plugins.html#Pycheckerplugin) - Provides support for [pychecker](http://pychecker.sourceforge.net/)
* [python.Pydev](http://pybuilder.github.io/documentation/plugins.html#ProjectfilesforEclipsePyDev) - Generates project files to import projects into [Eclipse PyDev](http://pydev.org/)
* [python.PyCharm](http://pybuilder.github.io/documentation/plugins.html#ProjectfilesforJetbrainsPyCharm) - Generates project files to import projects into [Jetbrains PyCharm](http://www.jetbrains.com/pycharm/)
* [python.pylint](http://pybuilder.github.io/documentation/plugins.html#Pylintplugin) - Executes [pylint](https://bitbucket.org/logilab/pylint/) on your sources.
* [python.pymetrics](http://pybuilder.github.io/documentation/plugins.html#Pymetricsplugin) - Calculates several metrics using [pymetrics](http://sourceforge.net/projects/pymetrics/)
* [python.unittest](http://pybuilder.github.com/documentation/plugins.html#RunningPythonUnittests) - Executes [unittest](http://docs.python.org/library/unittest.html) test cases
* [python.integrationtest](http://pybuilder.github.com/documentation/plugins.html#RunningPythonIntegrationTests) - Executes python scripts as integrations tests
* [python.pytddmon](http://pybuilder.github.io/documentation/plugins.html#Visualfeedbackfortests) - Provides visual feedback about unit tests through [pytddmon](http://pytddmon.org/)
* [python.cram](http://pybuilder.github.io/documentation/plugins.html#RunningCramtests) - Runs [cram](https://pypi.python.org/pypi/cram) tests

In addition, a few common plugins are provided:

* [copy_resources](http://pybuilder.github.io/documentation/plugins.html#Copyingresourcesintoadistribution) - Copies files.
* [filter_resources](http://pybuilder.github.io/documentation/plugins.html#Filteringfiles) - Filters files by replacing tokens with configuration values.
* [source_distribution](http://pybuilder.github.io/documentation/plugins.html#Creatingasourcedistribution) - Bundles a source distribution for shipping.

## Release Notes

The release notes can be found [here](http://pybuilder.github.com/releasenotes/)
