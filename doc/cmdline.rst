Flit command line interface
===========================

All operations use the ``flit`` command, followed by one of a number of
subcomamnds.

Common options
--------------

.. program:: flit

.. option:: -f <path>, --ini-file <path>

   Path to a config file specifying the module to build. The default is
   ``pyproject.toml`` or ``flit.ini``

.. option:: --repository <repository>

   Name of a repository to upload packages to. Should match a section in
   ``~/.pypirc``. The default is ``pypi``. See :doc:`upload`.

.. option::  --version

   Show the version of Flit in use.

.. option:: --help

   Show help on the command-line interface.

.. option:: --debug

   Show more detailed logs about what flit is doing.

``flit build``
--------------

.. program:: flit build

Build a wheel and an sdist (tarball) from the package.

.. option:: --format <format>

   Limit to building either ``wheel`` or ``sdist``.


``flit upload``
---------------

.. program:: flit upload

Build a wheel and an sdist (tarball) from the package, and upload them to PyPI
or another repository.

.. option:: --format <format>

   Limit to publishing either ``wheel`` or ``sdist``.
   You should normally publish the two formats together.

``flit install``
----------------

.. program:: flit install

Install the package on your system.

.. option:: -s, --symlink

   Symlink the module into site-packages rather than copying it, so that you
   can test changes without reinstalling the module.

.. option:: --pth-file

   Create a ``.pth`` file in site-packages rather than copying the module, so
   you can test changes without reinstalling. This is a less elegant alternative
   to ``--symlink``, but it works on Windows, which typically doesn't allow
   symlinks.

.. option:: --deps <dependency option>

   Which dependencies to install. One of ``all``, ``production``, ``develop``,
   or ``none``. Default ``all``.

``flit init``
-------------

.. program:: flit init

Create a new ``pyproject.toml``  config file by prompting for information about
the module in the current directory.
