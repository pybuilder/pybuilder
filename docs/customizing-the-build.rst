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

Installing non-python files is easily done with ``project.install_file(target, source)``.
The target path may be absolute, or relative to the installation prefix (``/usr/`` on most linux systems).

As an important sidenote, the path to ``source`` *must* be relative to the distribution directory.
Since non-python files are not copied to the distribution directory by default, it is necessary to use
the ``copy_resources`` plugin to include them.

Consider you want to install ``src/main/resources/my-config.yaml`` in ``/etc/defaults``.
It would be done like so:

First, we use copy_resources to copy the file into the distribution directory::

    use_plugin("copy_resources")

    @init
    def initialize(project):
        project.get_property("copy_resources_glob").append("src/main/resources/my-config.yaml")
        project.set_property("copy_resources_target", "$dir_dist")

Now, whenever copy_resources run, we will have the path ``src/main/resources/my-config.yaml`` copied
into ``target/dist/myproject-0.0.1/src/main/resources/my-config.yaml``.
We're now able to do::

    use_plugin("copy_resources")

    @init
    def initialize(project):
        project.get_property("copy_resources_glob").append("src/main/resources/my-config.yaml")
        project.set_property("copy_resources_target", "$dir_dist")
        project.install_file("/etc/defaults", "src/main/resources/my-config.yaml")

.. note::
    It's important to realize that the source path ``src/main/resources/my-config.yaml`` is NOT relative to
    the project root directory, but relative to the distribution directory instead. It just incidentally
    happens to be the same here.


Including files
^^^^^^^^^^^^^^^^^

Simply use the ``include_file`` directive::

    project.include_file(package_name, filename)

Tasks
******

Creating a task
----------------

To create a task, one can simply write a function in the ``build.py`` and annotate
it with the ``@task`` decorator.

::

    from pybuilder.core import task, init

    @init
    def initialize(project):
        pass

    @task
    def mytask(project, logger):
        logger.info("Hello from my task")

Like with initializer, PyBuilder will inject the arguments ``project``
and ``logger`` if the task function accepts them.

We'll now be able to call ``pyb mytask``.


The project API can be used to get configuration properties (so that the task is configurable).
It's also possible to compute paths by using ``expand_path``::

    from pybuilder.core import task

    @task
    def mytask(project, logger):
        logger.info("Will build the distribution in %s" % project.expand_path("$dir_dist"))


Task dependencies
------------------

A task can declare dependencies on other tasks by using the ``@depends`` decorator::

    from pybuilder.core import task, depends

    @task
    def task1(logger):
        logger.info("Hello from task1")

    @task
    @depends("task1")
    def task2(logger):
        logger.info("Hello from task2")

    @task
    @depends("task2", "run_unit_tests")
    def task3(logger):
        logger.info("Hello from task3")

Here, running task1 will just run task1. Running task2 will run task1 first, then task2.
Running task3 will run task1 first (dependency of task2), then run task2, then run unit tests,
and finally run task3.
