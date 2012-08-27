Pybuilder [![Build Status](https://secure.travis-ci.org/pybuilder/pybuilder.png?branch=master)](http://travis-ci.org/pybuilder/pybuilder)
=========

Pybuilder is a software build tool written in 100% pure Python and mainly 
targets Python applications.

Pybuilder is based on the concept of dependency based programming but also comes
along with powerful plugin mechanism that allows the construction of build life
cycles similar to those known from other famous (Java) build tools.

Pybuilder is running on the following versions of Python:

* 2.6
* 2.7
* 3.2

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
from pythonbuilder.core import use_plugin

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.coverage")
use_plugin("python.distutils")

default_task = "publish"
```

If you want to get started using Python Builder for your Python project, please
read the [Tutorial](http://code.google.com/p/python-builder/wiki/Tutorial).

There is also a [UsersGuide](http://code.google.com/p/python-builder/wiki/UsersGuide)
which is highly work in progress.

## Plugins

pybuilder provides a lot of plugins out ot the box that utilize tools and libraries commonly used in Python projects:

* **Coverage** - Uses the standard [coverage](http://pypi.python.org/pypi/coverage/) module to calculate unit test line coverage.
* **Setuptools** - Provides support to generate [setup.py](http://pypi.python.org/pypi/setuptools) files.
* **Django** - Provides support for developing [Django](https://www.djangoproject.com/) applications.
* **Flake8** - Provides support for [flake8](http://pypi.python.org/pypi/flake8/)
* **Pep8** - Provides support for [pep8](http://pypi.python.org/pypi/pep8)
* **Pychecker** - Provides support for [pychecker](http://pychecker.sourceforge.net/)
* **Pydev** - Generates project files to import projects into [Eclipse PyDev](http://pydev.org/)
* **Pylint** - Executes [pylint](http://www.logilab.org/857/) on your sources.
* **Pymetrics** - Calculates several metrics using
* **Pymetrics** - Calculates several metrics using [pymetrics](http://sourceforge.net/projects/pymetrics/)
* **Unittest** - Executes [unittest](http://docs.python.org/library/unittest.html) test cases

In addition, a few common plugins are provided:

* **copy_resources** - Copies files.
* **filter_resources** - Filters files by replacing tokens with configuration values.
* **source_distribution** - Bundles a source distribution for shipping.
