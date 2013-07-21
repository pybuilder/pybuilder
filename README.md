Pybuilder [![Build Status](https://secure.travis-ci.org/pybuilder/pybuilder.png?branch=master)](http://travis-ci.org/pybuilder/pybuilder) [![PyPi version](https://pypip.in/v/pybuilder/badge.png)](https://crate.io/packages/pybuilder/) [![PyPi downloads](https://pypip.in/d/pybuilder/badge.png)](https://crate.io/packages/pybuilder/) [![Coverage Status](https://coveralls.io/repos/pybuilder/pybuilder/badge.png?branch=master)](https://coveralls.io/r/pybuilder/pybuilder?branch=master)
=========

Pybuilder is a software build tool written in 100% pure Python and mainly
targets Python applications.

Pybuilder is based on the concept of dependency based programming but also comes
along with powerful plugin mechanism that allows the construction of build life
cycles similar to those known from other famous (Java) build tools.

Pybuilder is running on the following versions of Python: 2.6, 2.7, 3.2, 3.3 and PyPy.

See the [Travis Build](http://travis-ci.org/#!/pybuilder/pybuilder) for version specific output.

## Installing

Pybuilder is available using pip:

    $ pip install pybuilder

See the [Cheeseshop page](http://pypi.python.org/pypi/pybuilder/) for more
information.

## Getting started

Pybuilder emphasizes simplicity. If you want to build a pure Python project and
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

See the [pybuilder homepage](http://pybuilder.github.com/) for more details.

## Plugins

pybuilder provides a lot of plugins out ot the box that utilize tools and libraries commonly used in Python projects:

* [python.coverage](http://pybuilder.github.com/documentation/plugins.html#measuring_unittest_coverage) - Uses the standard [coverage](http://pypi.python.org/pypi/coverage/) module to calculate unit test line coverage.
* [python.distutils](http://pybuilder.github.com/documentation/plugins.html#building_a_python_egg) - Provides support to generate [setup.py](http://pypi.python.org/pypi/setuptools) files.
* **python.django** - Provides support for developing [Django](https://www.djangoproject.com/) applications.
* **python.flake8** - Provides support for [flake8](http://pypi.python.org/pypi/flake8/)
* **python.pep8** - Provides support for [pep8](http://pypi.python.org/pypi/pep8)
* **python.install_dependencies** - Installs the projects build and runtime dependencies using `pip`
* **python.pychecker** - Provides support for [pychecker](http://pychecker.sourceforge.net/)
* **python.Pydev** - Generates project files to import projects into [Eclipse PyDev](http://pydev.org/)
* **python.pylint** - Executes [pylint](http://www.logilab.org/857/) on your sources.
* **python.pymetrics** - Calculates several metrics using [pymetrics](http://sourceforge.net/projects/pymetrics/)
* [python.unittest](http://pybuilder.github.com/documentation/plugins.html#running_python_unittests) - Executes [unittest](http://docs.python.org/library/unittest.html) test cases
* [python.integrationtest](http://pybuilder.github.com/documentation/plugins.html#running_python_integration_tests) - Executes python scripts as integrations tests

In addition, a few common plugins are provided:

* **copy_resources** - Copies files.
* **filter_resources** - Filters files by replacing tokens with configuration values.
* **source_distribution** - Bundles a source distribution for shipping.

## Release Notes

The release notes can be found [here](http://pybuilder.github.com/releasenotes/)
