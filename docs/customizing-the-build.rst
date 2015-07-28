The build.py project descriptor
################################


The build.py anatomy
*********************

A ``build.py`` project descriptor consists of several parts:

Imports
---------

It's python code after all, so PyBuilder functions we use must be imported first.

::

    import os
    from pybuilder.core import task, init, use_plugin, Author

Plugin imports
---------------

Through usage of the ``use_plugin`` function, a plugin is loaded (its initializers
are registered for execution and any tasks are added to the available tasks).

::

    use_plugin("python.core")
    use_plugin("python.pycharm")

Project fields
---------------

Assigning to variables in the top-level of the build.py will set the corresponding fields
on the ``project`` object. Some of these fields are standardized (like ``authors``, ``name`` and ``version``).

::

        authors = [Author('John Doe', 'john@doe.invalid'),
                   Author('Jane Doe', 'jane@doe.invalid')]

        description = "This is the best project ever!"
        name = 'myproject'
        license = 'GNU GPL v3'
        version = '0.0.1'

        default_task = ['clean', 'analyze', 'publish']

Note that the above is equivalent to setting all the fields on ``project`` in an initializer,
though the first variant above is preferred for brevity's sake.

::

    @init
    def initialize(project):
        project.name = 'myproject'
        ...


Initializers
*************

An initializer is a function decorated by the ``@init`` decorator.
It is automatically collected by PyBuilder and executed before actual tasks
are executed.
The main use case of initializers is to mutate the ``project`` object in order to configure
plugins.

Dependency injection
---------------------

PyBuilder will automatically inject arguments by name into an initializer (provided the initializer accepts it).
The arguments ``project`` and ``logger`` are available currently.

This means that all of these are fine and will work as expected::

    @init
    def initialize():
        pass

    @init
    def initialize2(logger):
        pass

    @init
    def initialize3(project, logger):
        pass

    @init
    def initialize3(logger, project):
        pass

Environments
-------------

It's possible to execute an initializer only when a specific command-line switch was passed.
This is a bit akin to Maven's profiles::

    @init(environments='myenv')
    def initialize():
        pass

The above initializer will only get executed if we call ``pyb`` with the ``-E myenv`` switch.

The project object
-------------------

The project object is used to describe the project and plugin settings.
It also provides useful functions we can use to implement build logic.

Setting properties
^^^^^^^^^^^^^^^^^^^

PyBuilder uses a key-value based configuration for plugins.
In order to set configuration, ``project.set_property(name, value)`` is used.
For example we can tell the flake8 plugin to also lint our test sources with::

     project.set_property('flake8_include_test_sources', True)

In some cases we just want to mutate the properties (for example adding an element to a list),
this can be achieved with ``project.get_property(name)``. For example we can tell the
filter_resources plugin to apply on all files named ``setup.cfg``::

       project.get_property('filter_resources_glob').append('**/setup.cfg')

Note that ``append`` mutates the list.

Project dependencies
^^^^^^^^^^^^^^^^^^^^^

The project object tracks our project's dependencies.
There are several variants to add dependencies:

* ``project.depends_on(name)`` (runtime dependency)
* ``project.build_depends_on(name)`` (build-time dependency)
* ``project.depends_on(name, version)`` (where version is a pip version string like '==1.1.0' or '>=1.0')
* ``project.build_depends_on(name, version)`` (where version is a pip version string like '==1.1.0')

This will result on the install_dependencies plugin installing these dependencies when its task is called.
Runtime dependencies will also be added as metadata when packaging the project, for example building a python
setuptools tarball with a ``setup.py`` will fill the ``install_requires`` list.

Installing files
^^^^^^^^^^^^^^^^^


Including files
^^^^^^^^^^^^^^^^^

Tasks
******

Creating a task
----------------

Task dependencies
------------------
