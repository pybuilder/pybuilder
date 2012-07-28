Pybuilder [![Build Status](https://secure.travis-ci.org/pybuilder/pybuilder.png?branch=master)](http://travis-ci.org/pybuilder/pybuilder)
=========

Pybuilder is a software build tool written in 100% pure Python and mainly 
targets Python applications.

Pybuilder is based on the concept of dependency based programming but also comes
along with powerful plugin mechanism that allows the construction of build life
cycles similar to those known from other famous (Java) build tools.

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
read the Tutorial.

There is also a UsersGuide which is highly work in progress. The ListOfPlugins
may also provide some hints about what Python Builder can do. 
