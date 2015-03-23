User Documentaion
*******************



Pip and Easy Install
###########################



We recommend installing PyBuilder into a `virtual environment`_ using `pip`_:

``pip install pybuilder``

.. note:: Note
    At first it might seem tempting to install PyBuilder system-wide with ``sudo pip install pybuilder``, but if you work with virtualenvs then PyBuilder will see your system python (due to being installed there) instead of the virtualenv python.


Building from source
###########################



Please get the most recent version of PyBuilder first:

``git clone https://github.com/pybuilder/pybuilder
cd pybuilder``

Now to the bootstrapping part: install the dependencies and build PyBuilder… using PyBuilder!

``./bootstrap install_dependencies
./bootstrap``

Congratulations, you just built a binary distribution!

You can now head to ``target/dist/pybuilder-$VERSION`` and use the `distutils`_ ``setup.py`` installation script. Just type

``python setup.py install``


.. _virtual environment: http://pypi.python.org/pypi/virtualenv
.. _pip: http://pypi.python.org/pypi/pip
.. _distutils: http://docs.python.org/distutils/index.html
