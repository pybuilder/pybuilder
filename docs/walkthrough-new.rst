Complete walkthrough for a new PyBuilder project
#################################################

Installing PyBuilder
*********************

We'll start by creating a folder for our new project::

    mkdir myproject
    cd myproject

Then, onto creating a `virtualenv`_ and install PyBuilder inside it::

    virtualenv venv
    source venv/bin/activate
    pip install pybuilder

Scaffolding
************

Now we can use PyBuilder's own scaffolding capabilities::

        (venv) mriehl@isdeblnnl084 myproject $ pyb --start-project
        Project name (default: 'myproject') :
        Source directory (default: 'src/main/python') :
        Docs directory (default: 'docs') :
        Unittest directory (default: 'src/unittest/python') :
        Scripts directory (default: 'src/main/scripts') :
        Use plugin python.flake8 (Y/n)? (default: 'y') :
        Use plugin python.coverage (Y/n)? (default: 'y') :
        Use plugin python.distutils (Y/n)? (default: 'y') :

As you can see, this created the content roots automatically::

        (venv) mriehl@isdeblnnl084 myproject $ ll --tree
        inode Permissions Size Blocks User   Group  Date Modified Name
         1488 drwxr-xr-x     -      - mriehl admins 28 Jul 17:46  .
         1521 .rw-r--r--   324      8 mriehl admins 28 Jul 17:46  ├── build.py
         2844 drwxr-xr-x     -      - mriehl admins 28 Jul 17:46  ├── docs
         2143 drwxr-xr-x     -      - mriehl admins 28 Jul 17:46  └── src
         2789 drwxr-xr-x     -      - mriehl admins 28 Jul 17:46     ├── main
         2803 drwxr-xr-x     -      - mriehl admins 28 Jul 17:46     │  ├── python
         2864 drwxr-xr-x     -      - mriehl admins 28 Jul 17:46     │  └── scripts
         2827 drwxr-xr-x     -      - mriehl admins 28 Jul 17:46     └── unittest
         2829 drwxr-xr-x     -      - mriehl admins 28 Jul 17:46        └── python

Our new ``build.py``
*********************

Let us now take a look at the ``build.py`` which is the centralized project description for our new project.
The annotated contents are::

        from pybuilder.core import use_plugin, init

        # These are the plugins we want to use in our project.
        # Projects provide tasks which are blocks of logic executed by PyBuilder.

        use_plugin("python.core")
        # the python unittest plugin allows running python's standard library unittests
        use_plugin("python.unittest")
        # this plugin allows installing project dependencies with pip
        use_plugin("python.install_dependencies")
        # a linter plugin that runs flake8 (pyflakes + pep8) on our project sources
        use_plugin("python.flake8")
        # a plugin that measures unit test statement coverage
        use_plugin("python.coverage")
        # for packaging purposes since we'll build a tarball
        use_plugin("python.distutils")


        # The project name
        name = "myproject"
        # What PyBuilder should run when no tasks are given.
        # Calling "pyb" amounts to calling "pyb publish" here.
        # We could run several tasks by assigning a list to `default_task`.
        default_task = "publish"


        # This is an initializer, a block of logic that runs before the project is built.
        @init
        def set_properties(project):
            # Nothing happens here yet, but notice the `project` argument which is automatically injected.
            pass

Let's run PyBuilder and see what happens::

        (venv) mriehl@isdeblnnl084 myproject $ pyb
        PyBuilder version 0.10.63
        Build started at 2015-07-28 17:55:53
        ------------------------------------------------------------
        [INFO]  Building myproject version 1.0.dev0
        [INFO]  Executing build in /tmp/myproject
        [INFO]  Going to execute task publish
        [INFO]  Running unit tests
        [INFO]  Executing unit tests from Python modules in /tmp/myproject/src/unittest/python
        [WARN]  No unit tests executed.
        [INFO]  All unit tests passed.
        [INFO]  Building distribution in /tmp/myproject/target/dist/myproject-1.0.dev0
        [INFO]  Copying scripts to /tmp/myproject/target/dist/myproject-1.0.dev0/scripts
        [INFO]  Writing setup.py as /tmp/myproject/target/dist/myproject-1.0.dev0/setup.py
        [INFO]  Collecting coverage information
        [INFO]  Running unit tests
        [INFO]  Executing unit tests from Python modules in /tmp/myproject/src/unittest/python
        [WARN]  No unit tests executed.
        [INFO]  All unit tests passed.
        [WARN]  Overall coverage is below 70%:  0%
        Coverage.py warning: No data was collected.
        ------------------------------------------------------------
        BUILD FAILED - Test coverage for at least one module is below 70%
        ------------------------------------------------------------
        Build finished at 2015-07-28 17:55:54
        Build took 0 seconds (515 ms)

We don't have any tests so our coverage is zero percent, all right!
We have two ways to go about this - coverage breaks the build by default, so we
can (if we want to) choose to not break the build based on the coverage metrics.
This logic belongs to the project build, so we would have to add it to our build.py
in the initializer. You can think of the initializer as a function that sets some configuration values
before PyBuilder moves on to the actual work::

        # This is an initializer, a block of logic that runs before the project is built.
        @init
        def set_properties(project):
            project.set_property("coverage_break_build", False) # default is True

With the above modification, the coverage plugin still complains but it does not break the build.
Since we're clean coders, we're going to add some production code with a test though!

Our first test
***************

We'll write an application that outputs "Hello world".
Let's start with a test at ``src/unittest/python/myproject_tests.py``::
        from unittest import TestCase

        from mock import Mock

        from myproject import greet


        class Test(TestCase):

            def test_should_write_hello_world(self):
                mock_stdout = Mock()

                greet(mock_stdout)

                mock_stdout.write.assert_called_with("Hello world!\n")

.. note::
   As a default, the unittest plugin finds tests if their filename ends with ``_tests.py``.
   We could change this with a well-placed ``project.set_property`` of course.

Our first dependency
---------------------

Since we're using mock, we'll have to install it by telling our initializer
in ``build.py`` about it::

        # This is an initializer, a block of logic that runs before the project is built.
        @init
        def set_properties(project):
            project.set_property("coverage_break_build", False) # default is True
            project.build_depends_on("mock")

We could require a specific version and so on but let's keep it simple.
Also note that we declared ``mock`` as a build dependency - this means it's only required
for building and if we upload our project to PyPI then installing it from there will not require
installing ``mock``.

We can install our dependency by running PyBuilder with the corresponding task::

        (venv) mriehl@isdeblnnl084 myproject $ pyb install_dependencies
        PyBuilder version 0.10.63
        Build started at 2015-07-28 19:35:37
        ------------------------------------------------------------
        [INFO]  Building myproject version 1.0.dev0
        [INFO]  Executing build in /tmp/myproject
        [INFO]  Going to execute task install_dependencies
        [INFO]  Installing all dependencies
        [INFO]  Installing build dependencies
        [INFO]  Installing dependency 'coverage'
        [INFO]  Installing dependency 'flake8'
        [INFO]  Installing dependency 'mock'
        [INFO]  Installing runtime dependencies
        ------------------------------------------------------------
        BUILD SUCCESSFUL
        ------------------------------------------------------------
        Build Summary
                     Project: myproject
                     Version: 1.0.dev0
              Base directory: /tmp/myproject
                Environments:
                       Tasks: install_dependencies [1480 ms]
        Build finished at 2015-07-28 19:35:39
        Build took 1 seconds (1486 ms)
        pyb install_dependencies  1.44s user 0.10s system 98% cpu 1.570 total

Running our test
-----------------

We can run our test now::

        (venv) mriehl@isdeblnnl084 myproject $ pyb verify
        PyBuilder version 0.10.63
        Build started at 2015-07-28 19:36:41
        ------------------------------------------------------------
        [INFO]  Building myproject version 1.0.dev0
        [INFO]  Executing build in /tmp/myproject
        [INFO]  Going to execute task verify
        [INFO]  Running unit tests
        [INFO]  Executing unit tests from Python modules in /tmp/myproject/src/unittest/python
        [ERROR] Import error in test file /tmp/myproject/src/unittest/python/myproject_tests.py, due to statement 'from myproject import greet' on line 5
        [ERROR] Error importing unittest: No module named myproject
        ------------------------------------------------------------
        BUILD FAILED - Unable to execute unit tests.
        ------------------------------------------------------------
        Build finished at 2015-07-28 19:36:41
        Build took 0 seconds (249 ms)

It's still failing because we haven't implemented anything yet. Let's do that right now
in ``src/main/python/myproject/__init__.py``::

        def greet(filelike):
            filelike.write("Hello world!\n")

Any finally rerun the test::

        (venv) mriehl@isdeblnnl084 myproject $ pyb verify
        PyBuilder version 0.10.63
        Build started at 2015-07-28 19:39:15
        ------------------------------------------------------------
        [INFO]  Building myproject version 1.0.dev0
        [INFO]  Executing build in /tmp/myproject
        [INFO]  Going to execute task verify
        [INFO]  Running unit tests
        [INFO]  Executing unit tests from Python modules in /tmp/myproject/src/unittest/python
        [INFO]  Executed 1 unit tests
        [INFO]  All unit tests passed.
        [INFO]  Building distribution in /tmp/myproject/target/dist/myproject-1.0.dev0
        [INFO]  Copying scripts to /tmp/myproject/target/dist/myproject-1.0.dev0/scripts
        [INFO]  Writing setup.py as /tmp/myproject/target/dist/myproject-1.0.dev0/setup.py
        [INFO]  Collecting coverage information
        [INFO]  Running unit tests
        [INFO]  Executing unit tests from Python modules in /tmp/myproject/src/unittest/python
        [INFO]  Executed 1 unit tests
        [INFO]  All unit tests passed.
        [INFO]  Overall coverage is 100%
        ------------------------------------------------------------
        BUILD SUCCESSFUL
        ------------------------------------------------------------
        Build Summary
                     Project: myproject
                     Version: 1.0.dev0
              Base directory: /tmp/myproject
                Environments:
                       Tasks: prepare [231 ms] compile_sources [0 ms] run_unit_tests [10 ms] package [1 ms] run_integration_tests [0 ms] verify [255 ms]
        Build finished at 2015-07-28 19:39:15
        Build took 0 seconds (504 ms)

Adding a script
****************

Since our library is ready, we can now add a script.

We'll just need to create ``src/main/scripts/greeter``::

        #!/usr/bin/env python
        import sys
        from myproject import greet

        greet(sys.stdout)

Note that there is nothing else to do. Dropping the file in ``src/main/scripts`` is all we need to do
for PyBuilder to pick it up, because this is the convention.

Let's look at what happens when we package it up::

        (venv) mriehl@isdeblnnl084 myproject $ pyb publish
        PyBuilder version 0.10.63
        Build started at 2015-07-28 19:44:34
        ------------------------------------------------------------
        [INFO]  Building myproject version 1.0.dev0
        [INFO]  Executing build in /tmp/myproject
        [INFO]  Going to execute task publish
        [INFO]  Running unit tests
        [INFO]  Executing unit tests from Python modules in /tmp/myproject/src/unittest/python
        [INFO]  Executed 1 unit tests
        [INFO]  All unit tests passed.
        [INFO]  Building distribution in /tmp/myproject/target/dist/myproject-1.0.dev0
        [INFO]  Copying scripts to /tmp/myproject/target/dist/myproject-1.0.dev0/scripts
        [INFO]  Writing setup.py as /tmp/myproject/target/dist/myproject-1.0.dev0/setup.py
        [INFO]  Collecting coverage information
        [INFO]  Running unit tests
        [INFO]  Executing unit tests from Python modules in /tmp/myproject/src/unittest/python
        [INFO]  Executed 1 unit tests
        [INFO]  All unit tests passed.
        [INFO]  Overall coverage is 100%
        [INFO]  Building binary distribution in /tmp/myproject/target/dist/myproject-1.0.dev0
        ------------------------------------------------------------
        BUILD SUCCESSFUL
        ------------------------------------------------------------
        Build Summary
                     Project: myproject
                     Version: 1.0.dev0
              Base directory: /tmp/myproject
                Environments:
                       Tasks: prepare [227 ms] compile_sources [0 ms] run_unit_tests [9 ms] package [2 ms] run_integration_tests [0 ms] verify [252 ms] publish [241 ms]
        Build finished at 2015-07-28 19:44:35
        Build took 0 seconds (739 ms)

We can now simply ``pip install`` the tarball::

        (venv) mriehl@isdeblnnl084 myproject $ pip install target/dist/myproject-1.0.dev0/dist/myproject-1.0.dev0.tar.gz
        Processing ./target/dist/myproject-1.0.dev0/dist/myproject-1.0.dev0.tar.gz
        Building wheels for collected packages: myproject
          Running setup.py bdist_wheel for myproject
          Stored in directory: /data/home/mriehl/.cache/pip/wheels/89/05/9e/4b035292abf39e5d6ddcf442cc7c96c2e56f5cc49c5c673d3a
        Successfully built myproject
        Installing collected packages: myproject
        Successfully installed myproject-1.0.dev0
        (venv) mriehl@isdeblnnl084 myproject $ greeter
        Hello world!

Of course since there is a ``setup.py`` in the distribution folder, we can use
it to do whatever we want easily, for example uploading to PyPI::

        (venv) mriehl@isdeblnnl084 myproject $ cd target/dist/myproject-1.0.dev0/
        (venv) mriehl@isdeblnnl084 myproject-1.0.dev0 $ python setup.py upload


.. _virtualenv: https://pypi.python.org/pypi/virtualenv
