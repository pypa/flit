Developing Flit
===============

To get a development installation of Flit itself::

    git clone https://github.com/takluyver/flit.git
    cd flit
    python3 -m pip install docutils requests pytoml
    python3 bootstrap_dev.py

This links Flit into the current Python environment, so you can make changes
and try them without having to reinstall each time.

Testing
-------

To run the tests in separate environments for each available Python version::

    tox

`tox <https://tox.readthedocs.io/en/latest/>`_ has many options.

To run the tests in your current environment, run::

    pytest

