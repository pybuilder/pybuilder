[PyBuilder &#x2014; an easy-to-use build automation tool for Python](https://pybuilder.io)
=========

[![Follow PyBuilder on Twitter](https://img.shields.io/twitter/follow/pybuilder_?label=Follow%20PyBuilder&style=social)](https://twitter.com/intent/follow?screen_name=pybuilder_)
[![Gitter](https://img.shields.io/gitter/room/pybuilder/pybuilder?logo=gitter)](https://app.gitter.im/#/room/#pybuilder_pybuilder:gitter.im)
[![Build Status](https://img.shields.io/github/actions/workflow/status/pybuilder/pybuilder/pybuilder.yml?branch=master)](https://github.com/pybuilder/pybuilder/actions/workflows/pybuilder.yml)
[![Coverage Status](https://img.shields.io/coveralls/github/pybuilder/pybuilder/master?logo=coveralls)](https://coveralls.io/r/pybuilder/pybuilder?branch=master)

[![PyBuilder Version](https://img.shields.io/pypi/v/pybuilder?logo=pypi)](https://pypi.org/project/pybuilder/)
[![PyBuilder Python Versions](https://img.shields.io/pypi/pyversions/pybuilder?logo=pypi)](https://pypi.org/project/pybuilder/)
[![PyBuilder Downloads Per Day](https://img.shields.io/pypi/dd/pybuilder?logo=pypi)](https://pypi.org/project/pybuilder/)
[![PyBuilder Downloads Per Week](https://img.shields.io/pypi/dw/pybuilder?logo=pypi)](https://pypi.org/project/pybuilder/)
[![PyBuilder Downloads Per Month](https://img.shields.io/pypi/dm/pybuilder?logo=pypi)](https://pypi.org/project/pybuilder/)

PyBuilder is a software build tool written in 100% pure Python, mainly
targeting Python applications.

PyBuilder is based on the concept of dependency based programming, but it also
comes with a powerful plugin mechanism, allowing the construction of build life
cycles similar to those known from other famous (Java) build tools.

PyBuilder is running on the following versions of Python 3.7, 3.8, 3.9, 3.10, 3.11 and PyPy 3.7, 3.8 and 3.9.

See the [GitHub Actions Workflow](https://github.com/pybuilder/pybuilder/actions/workflows/pybuilder.yml) for version specific output.

## Installing

PyBuilder is available using pip:

    $ pip install pybuilder

For development builds use:

    $ pip install --pre pybuilder

See the [PyPI](https://pypi.org/project/pybuilder/) for more information.

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

See the [PyBuilder homepage](https://pybuilder.io) for more details and
a list of plugins.

## Release Notes

The release notes can be found [here](https://pybuilder.io/release-notes/).
There will also be a git tag with each release. Please note that we do not currently promote tags to GitHub "releases".

## Development
See [Developing PyBuilder](https://pybuilder.io/documentation/developing-pybuilder)
