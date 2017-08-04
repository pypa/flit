**Flit** is a simple way to put Python packages and modules on PyPI.

Say you're writing a module ``foobar``—either as a single file ``foobar.py``,
or as a directory—and you want to distribute it.

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
       home-page=http://github.com/sirrobin/foobar

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

If your package is not registered on PyPI yet, flit will try to register it for
you during the upload step. 

To install a package locally for development, run::

    flit install [--symlink] [--python path/to/python]

Flit packages a single importable module or package at a time, using the import
name as the name on PyPI. All subpackages and data files within a package are
included automatically.

Flit requires Python 3, but you can use it to distribute modules for Python 2,
so long as they can be imported on Python 3.

To publish a package to TestPyPI:

1. Edit your ``~/.pypirc`` file as follows::

       [distutils]
       index-servers =
           pypi
           testpypi

       [testpypi]
       repository = https://test.pypi.org/legacy/
       username:<your_testPyPI_username>
       password:<your_testPyPI_password>

       [pypi]
       username:<your_PyPI_username>
       password:<your_PyPI_password>

2. Run this command to upload your code to TestPyPI::

       flit --repository testpypi publish


`See Flit's documentation <https://flit.readthedocs.io/>`_ for more
information.
