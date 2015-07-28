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
        # for packaging purposes since we'll build a tarball and RPM.
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


.. _virtualenv: https://pypi.python.org/pypi/virtualenv
