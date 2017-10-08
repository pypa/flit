**Flit** is a simple way to put Python packages and modules on PyPI.

Install
-------

::

    $ pip install flit

Flit requires Python 3 and therefor needs to be installed using the Python 3
version of PIP. On some platforms (including Debian, Ubuntu and Fedora) this
means that you'll have to use the ``pip3`` command instead to get the correct
interpreter version.

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

2. Create a file ``flit.ini`` next to the module. It should look like this:

   .. code-block:: ini

       [metadata]
       module=foobar
       author=Sir Robin
       author-email=robin@camelot.uk
       home-page=https://github.com/sirrobin/foobar

       # If you want command line scripts, this is how to declare them.
       # If not, you can leave this section out completely.
       [scripts]
       # foobar:main means the script will do: from foobar import main; main()
       foobar=foobar:main

   You can use ``flit init`` to easily create a basic ``flit.ini`` file for your
   package.

   Besides the details shown above, there are other fields you can add—see the
   `flit.ini page <https://flit.readthedocs.io/en/latest/flit_ini.html>`_
   of the docs.

3. Install flit if you don't already have it::

       pip install flit

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
