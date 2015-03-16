**Flit** is a simple way to put Python packages and modules on PyPI.

Say you're writing a module ``foobar.py`` and you want to distribute it.

1. Make sure that foobar's docstring starts with a one-line summary of what
   the module is, and that it has a ``__version__``:

   .. code-block:: python

       """An amazing sample package!"""

        __version__ = '0.1'

2. Create a file ``foobar-pypi.ini``—or ``foobar/pypi.ini`` if foobar is
   a package. It should look like this:

   .. code-block:: ini

       [metadata]
       author=Sir Robin
       author-email=robin@camelot.uk
       home-page=http://github.com/sirrobin/foobar

       # If you want command line scripts, this is how to declare them.
       # If not, you can leave this section out completely.
       [scripts]
       # foobar:main means the script will do: from foobar import main; main()
       foobar=foobar:main

   There are other fields you can add - see the pypi.ini page of the docs.

3. Run this command to upload your code to PyPI::

       flit path/to/foobar.py wheel --upload

To install a package locally for development, run::

    flit path/to/foobar.py install [--symlink]

Flit packages a single importable module or package at a time, using the import
name as the name on PyPI. All subpackages and data files within a package are
included automatically.

Flit requires Python 3, but you can use it to distribute modules for Python 2,
so long as they can be imported on Python 3.
