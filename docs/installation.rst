Installation
####################

PyBuilder is available on PyPI, so you can install it with

``$ pip install pybuilder``

Virtual Environment
******************************

We recommend installing PyBuilder into a `virtual environment`_ using `pip`_:

``$ virtualenv venv``

.. note::
    At first it might seem tempting to install PyBuilder system-wide with ``sudo pip install pybuilder``, but if you work with virtualenvs then PyBuilder will see your system python (due to being installed there) instead of the virtualenv python.


Installing completions
*****************************

If you are a zsh or fish shell user, we recommend installing the `pybuilder-completions`_.
These will provide tab-based completions for PyBuilder options and tasks on a per-project basis.

``sudo pip install pybuilder-completions``

.. note::
    The completions can be installed system-wide since they are just files for the relevant shells.

.. _virtual environment: https://pypi.python.org/pypi/virtualenv
.. _pip: https://pypi.python.org/pypi/pip
.. _pybuilder-completions: https://pypi.python.org/pypi/pybuilder-completions
