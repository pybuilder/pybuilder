PyBuilder
=========

[PyBuilder](http://pybuilder.github.io)


[![Gitter](https://badges.gitter.im/pybuilder/pybuilder.svg)](https://gitter.im/pybuilder/pybuilder)
[![Build Status](https://secure.travis-ci.org/pybuilder/pybuilder.png?branch=master)](http://travis-ci.org/pybuilder/pybuilder)
[![Windows build status](https://ci.appveyor.com/api/projects/status/e8fbgcyc7bdqbko3?svg=true)](https://ci.appveyor.com/project/mriehl/pybuilder)
[![PyPI version](https://badge.fury.io/py/pybuilder.png)](https://warehouse.python.org/project/pybuilder/)
[![Coverage Status](https://coveralls.io/repos/pybuilder/pybuilder/badge.png?branch=master)](https://coveralls.io/r/pybuilder/pybuilder?branch=master)
[![Ready in backlog](https://badge.waffle.io/pybuilder/pybuilder.png?label=ready&title=Ready)](https://waffle.io/pybuilder/pybuilder)
[![Open bugs](https://badge.waffle.io/pybuilder/pybuilder.png?label=bug&title=Open%20Bugs)](https://waffle.io/pybuilder/pybuilder)

PyBuilder is a software build tool written in 100% pure Python, mainly
targeting Python applications.

PyBuilder is based on the concept of dependency based programming, but it also
comes with a powerful plugin mechanism, allowing the construction of build life
cycles similar to those known from other famous (Java) build tools.

PyBuilder is running on the following versions of Python: 2.7, 3.4, 3.5, 3.6, 3.7, PyPy 2.7, and PyPy 3.5.

See the [Travis Build](https://travis-ci.org/pybuilder/pybuilder) for version specific output.

## Installing

PyBuilder is available using pip:

    $ pip install pybuilder

For development builds use:

    $ pip install --pre pybuilder

See the [Cheeseshop page](https://warehouse.python.org/project/pybuilder/) for more
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

See the [PyBuilder homepage](http://pybuilder.github.com/) for more details and
a list of plugins.

## Release Notes

The release notes can be found [here](http://pybuilder.github.com/releasenotes/).
There will also be a git tag with each release. Please note that we do not currently promote tags to GitHub "releases".

## Development
See [developing PyBuilder](http://pybuilder.github.io/documentation/developing_pybuilder.html)
