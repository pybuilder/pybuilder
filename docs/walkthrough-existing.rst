Walkthrough working on an existing PyBuilder project
#####################################################

Getting the project
*********************

We'll use `yadtshell`_ as an example to checkout and build a PyBuilder project from scratch.

Begin by cloning the git project:

``git clone https://github.com/yadt/yadtshell``

and then move into the new directory:

``cd yadtshell``


Ensuring your environment is ready
***********************************

Please make sure you have `virtualenv`_ installed. You will need it to isolate the yadtshell dependencies
from your system python.

Now go ahead and create a new virtualenv (we'll name it ``venv``):

``virtualenv venv``

You can now make the virtualenv active by sourcing its activate script:

``source venv/bin/activate``

Now install PyBuilder in your new virtualenv:

``pip install pybuilder``


Building the project
*********************

We're finally ready to build our project.
You can start by asking PyBuilder what tasks it knows about::

        (venv) mriehl@isdeblnnl084 yadtshell (git)-[master] $ pyb -t
        Tasks found for project "yadtshell":
                                 analyze - Execute analysis plugins.  
                                           depends on tasks: run_unit_tests prepare prepare
                                   clean - Cleans the generated output. 
                         compile_sources - Compiles source files that need compilation.
                                           depends on tasks: prepare
            generate_manpage_with_pandoc - <no description available>
              install_build_dependencies - Installs all build dependencies specified in the build descriptor
                    install_dependencies - Installs all (both runtime and build) dependencies specified in the build descriptor
            install_runtime_dependencies - Installs all runtime dependencies specified in the build descriptor
                       list_dependencies - Displays all dependencies the project requires
                                 package - Packages the application. Package a python application. 
                                           depends on tasks: run_unit_tests
                                 prepare - Prepares the project for building.
                                 publish - Publishes the project.
                                           depends on tasks: verify
                   run_integration_tests - Runs integration tests on the packaged application. Runs integration tests based on Python's unittest module
                                           depends on tasks: package
                      run_sonar_analysis - Launches sonar-runner for analysis.
                                           depends on tasks: analyze
                          run_unit_tests - Runs all unit tests. Runs unit tests based on Python's unittest module
                                           depends on tasks: compile_sources
                                  verify - Verifies the project and possibly integration tests.
                                           depends on tasks: run_integration_tests

You can call any of these tasks (PyBuilder will ensure dependencies are satisfied)::

    pyb clean analyze

The most obvious task to start with is installing the project dependencies - PyBuilder makes a distinction between
run-time (a hipster async library for example) and build-time dependencies (a test framework).
You can simply install all dependencies with::

    pyb install_dependencies

There are also other tasks (``install_build_dependencies`` and ``install_runtime_dependencies``) for more fine-grained control.

PyBuilder comes with a "default goal" so that building is easy - per convention this means that when not
given any tasks, PyBuilder will perform all the tasks deemed useful by the project developers.
So in general, building your project is as simple as::

        (venv) mriehl@isdeblnnl084 yadtshell (git)-[master] $ pyb
        PyBuilder version 0.10.63
        Build started at 2015-07-28 09:50:00
        ------------------------------------------------------------
        [INFO]  Building yadtshell version 1.9.2
        [INFO]  Executing build in /data/home/mriehl/workspace/yadtshell
        [INFO]  Going to execute tasks: clean, analyze, publish
        [INFO]  Removing target directory /data/home/mriehl/workspace/yadtshell/target
        [INFO]  Removing yadtshell log directory: /tmp/logs/yadtshell/2015-07-28
        [INFO]  Removing yadtshell integration test stubs directory: /tmp/yadtshell-it
        [INFO]  Removing yadtshell state directory: /data/home/mriehl/.yadtshell
        [INFO]  Executing unittest Python modules in /data/home/mriehl/workspace/yadtshell/src/unittest/python
        [INFO]  Executed 289 unittests
        [INFO]  All unittests passed.
        [INFO]  Executing flake8 on project sources.
        [INFO]  Executing frosted on project sources.
        [INFO]  Collecting coverage information
        [INFO]  Executing unittest Python modules in /data/home/mriehl/workspace/yadtshell/src/unittest/python
        [INFO]  Executed 289 unittests
        [INFO]  All unittests passed.
        [WARN]  Test coverage below 50% for yadtshell.restart: 29%
        [WARN]  Test coverage below 50% for yadtshell.actionmanager: 40%
        [WARN]  Test coverage below 50% for yadtshell.dump: 17%
        [WARN]  Module not imported: yadtshell.broadcast. No coverage information available.
        [WARN]  Test coverage below 50% for yadtshell.TerminalController: 42%
        [INFO]  Overall coverage is 65%
        [INFO]  Building distribution in /data/home/mriehl/workspace/yadtshell/target/dist/yadtshell-1.9.2
        [INFO]  Copying scripts to /data/home/mriehl/workspace/yadtshell/target/dist/yadtshell-1.9.2/scripts
        [INFO]  Copying resources matching 'setup.cfg docs/man/yadtshell.1.man.gz' from /data/home/mriehl/workspace/yadtshell to /data/home/mriehl/workspace/yadtshell/target/dist/yadtshell-1.9.2
        [INFO]  Filter resources matching **/yadtshell/__init__.py **/scripts/yadtshell **/setup.cfg in /data/home/mriehl/workspace/yadtshell/target
        [WARN]  Skipping impossible substitution for 'GREEN' - there is no matching project attribute or property.
        [WARN]  Skipping impossible substitution for 'BOLD' - there is no matching project attribute or property.
        [WARN]  Skipping impossible substitution for 'NORMAL' - there is no matching project attribute or property.
        [WARN]  Skipping impossible substitution for 'BG_YELLOW' - there is no matching project attribute or property.
        [WARN]  Skipping impossible substitution for 'BOLD' - there is no matching project attribute or property.
        [WARN]  Skipping impossible substitution for 'NORMAL' - there is no matching project attribute or property.
        [WARN]  Skipping impossible substitution for 'RED' - there is no matching project attribute or property.
        [WARN]  Skipping impossible substitution for 'BOLD' - there is no matching project attribute or property.
        [WARN]  Skipping impossible substitution for 'NORMAL' - there is no matching project attribute or property.
        [INFO]  Writing MANIFEST.in as /data/home/mriehl/workspace/yadtshell/target/dist/yadtshell-1.9.2/MANIFEST.in
        [INFO]  Writing setup.py as /data/home/mriehl/workspace/yadtshell/target/dist/yadtshell-1.9.2/setup.py
        [INFO]  Running integration tests in parallel
        [--------------------------------------------------------------------] 
        [INFO]  Executed 68 integration tests.
        [INFO]  Building binary distribution in /data/home/mriehl/workspace/yadtshell/target/dist/yadtshell-1.9.2
        ------------------------------------------------------------
        BUILD SUCCESSFUL
        ------------------------------------------------------------
        Build Summary
                     Project: yadtshell
                     Version: 1.9.2
              Base directory: /data/home/mriehl/workspace/yadtshell
                Environments: 
                       Tasks: clean [30 ms] prepare [282 ms] compile_sources [0 ms] run_unit_tests [951 ms] analyze [2679 ms] package [26 ms] run_integration_tests [26305 ms] verify [0 ms] publish [523 ms]
        Build finished at 2015-07-28 09:50:31
        Build took 30 seconds (30812 ms)
        pyb  42.96s user 8.21s system 165% cpu 30.918 total


.. _yadtshell: https://github.com/yadt/yadtshell
.. _virtualenv: https://pypi.python.org/pypi/virtualenv

