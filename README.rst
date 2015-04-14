**Flit** is a simple way to put Python packages and modules on PyPI.

Say you're writing a module ``foobar``—either as a single file ``foobar.py``,
or as a directory—and you want to distribute it.

1. Make sure that foobar's docstring starts with a one-line summary of what
   the module is, and that it has a ``__version__``:

   .. code-block:: python

       """An amazing sample package!"""

       __version__ = '0.1'

2. Install flit if you don't already have it::

       pip install flit

3. Generate a flit init using `flit int`:

     .. code-block:: shell
        $ flit init
        Module name: flit
        Author [Thomas kluyver]:
        Author email [myemail@gmail.com]:
        Home page [https://github.com/takluyver/flit]:
        Choose a license
        1. BSD - simple and permissive
        2. Apache - explicitly grants patent rights
        3. GPL - ensures that code based on this is shared with the same terms
        4. Skip - choose a license later
        Enter 1-4 [1]: 1

        Written flit.ini; edit that file to add optional extra info.

Flit is smart enough to propose some default values based on the previous one you entered !

For extra configuration, see how to edit the `flit.ini` file in the docs.

4. Run this command to upload your code to PyPI::

       flit wheel --upload

If your package is not registered on PyPI yet, flit will try to register it for
you during the upload step. 

To install a package locally for development, run::

    flit install [--symlink]

.. note::

   Flit only creates packages in the new 'wheel' format. People using older
   versions of pip (<1.5) or easy_install will not be able to install them.
   People may also want a traditional sdist for other reasons, such as Linux
   distro packaging. I hope that these problems will diminsh over time.

Flit packages a single importable module or package at a time, using the import
name as the name on PyPI. All subpackages and data files within a package are
included automatically.

Flit requires Python 3, but you can use it to distribute modules for Python 2,
so long as they can be imported on Python 3.
