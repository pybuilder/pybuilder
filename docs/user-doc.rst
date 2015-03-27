User Documentaion
*******************



Quickstart using pip
####################


Virtual Environment
------------------------------

We recommend installing PyBuilder into a `virtual environment`_ using `pip`_:

``$ virtualenv venv``

.. note:: Note
  venv ist just the name of the virtualenv folder, you can use avery name you want, like ``foo`` or ``bar``

``$ pip install pybuilder``

.. note:: Note
    At first it might seem tempting to install PyBuilder system-wide with ``sudo pip install pybuilder``, but if you work with virtualenvs then PyBuilder will see your system python (due to being installed there) instead of the virtualenv python.


Start your first project from scratch
######################################

``$ pyb --start-project``

.. note:: Note
  Pybuilder will ask you some questions about your ``Project name``, `Source directory`_, ``Unittest directory``, ``Scripts directory`` and it will suggest to install
  some default plugins like ``flake8`` for code linting, ``coverage`` for messuring coverage of your tests and `distutils`_ to `package your application`_


pybuider created a `build.py`_ file, a description file were you configure your project informations like dependencies and some other meta informations


install your dependencies
---------------------------------------

.. note:: Note
  if you chose to use the default plugins via ``--start-project`` you have to install this plugins via ``install_dependencies``

``$ pyb install_dependencies``

.. code-block:: bash

  PyBuilder version 0.10.58
  Build started at 2015-03-27 13:48:29
  ------------------------------------------------------------
  [INFO]  Building foo version 1.0.dev0
  [INFO]  Executing build in /Users/mwolf/workdir/foo
  [INFO]  Going to execute task install_dependencies
  [INFO]  Installing all dependencies
  [INFO]  Installing build dependencies
  [INFO]  Installing dependency 'coverage'
  [INFO]  Installing dependency 'flake8'
  [INFO]  Installing runtime dependencies
  ------------------------------------------------------------
  BUILD SUCCESSFUL
  ------------------------------------------------------------
  Build Summary
             Project: foo
             Version: 1.0.dev0
      Base directory: /Users/mwolf/workdir/foo
        Environments:
               Tasks: install_dependencies [2336 ms]
  Build finished at 2015-03-27 13:48:32
  Build took 2 seconds (2353 ms)



Migrate a project to PyBuilder
#################################




.. _virtual environment: http://pypi.python.org/pypi/virtualenv
.. _pip: http://pypi.python.org/pypi/pip
.. _distutils: http://docs.python.org/distutils/index.html
.. _Source directory: project-structure.html
.. _package your application: build-software.html
.. _build.py: build-py.html

