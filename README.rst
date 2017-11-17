**Flit** is a simple way to put Python packages and modules on PyPI.

Install
-------

::

    $ python3 -m pip install flit

Flit requires Python 3 and therefore needs to be installed using the Python 3
version of pip.

Python 2 modules can be distributed using Flit, but need to be importable on
Python 3 without errors.

Usage
-----

Say you're writing a module ``foobar`` — either as a single file ``foobar.py``,
or as a directory — and you want to distribute it.

1. Make sure that foobar's docstring starts with a one-line summary of what
   the module is, and that it has a ``__version__``:

   .. code-block:: python

       """An amazing sample package!"""

       __version__ = '0.1'

2. Install flit if you don't already have it::

       python3 -m pip install flit

3. Run ``flit init`` to create a ``pyproject.toml`` file. It will look something
   like this:

   .. code-block:: ini

       [build-system]
       requires = ["flit"]
       build-backend = "flit.buildapi"

       [tool.flit.metadata]
       module = "foobar"
       author = "Sir Robin"
       author-email = "robin@camelot.uk"
       home-page = "https://github.com/sirrobin/foobar"

   You can edit this file to add other metadata, for example to set up
   command line scripts. See the
   `flit.ini page <https://flit.readthedocs.io/en/latest/flit_ini.html>`_
   of the docs.

   If you have already got a ``flit.ini`` file to use with older versions of
   Flit, it will still work for now, but you should convert it to
   ``pyproject.toml`` when convenient.

4. Run this command to upload your code to PyPI::

       flit publish

To install a package locally for development, run::

    flit install [--symlink] [--python path/to/python]

Flit packages a single importable module or package at a time, using the import
name as the name on PyPI. All subpackages and data files within a package are
included automatically.

Documentation
-------------

See `Flit's documentation <https://flit.readthedocs.io/>`_ for more
information.
