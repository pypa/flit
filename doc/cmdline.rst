Flit command line interface
===========================

All operations use the ``flit`` command, followed by one of a number of
subcommands.

Common options
--------------

.. program:: flit

.. option:: -f <path>, --ini-file <path>

   Path to a config file specifying the module to build. The default is
   ``pyproject.toml``.

.. option::  --version

   Show the version of Flit in use.

.. option:: --help

   Show help on the command-line interface.

.. option:: --debug

   Show more detailed logs about what flit is doing.

.. _build_cmd:

``flit build``
--------------

.. program:: flit build

Build a wheel and an sdist (tarball) from the package.

.. option:: --format <format>

   Limit to building either ``wheel`` or ``sdist``.

.. option:: --setup-py

   Generate a ``setup.py`` file in the sdist, so it can be installed by older
   versions of pip.

.. option:: --no-setup-py

   Don't generate a setup.py file in the sdist. This is the default.
   An sdist built without this will only work with tools that support PEP 517,
   but the wheel will still be usable by any compatible tool.

   .. versionchanged:: 3.5

      Generating ``setup.py`` disabled by default.

.. option:: --use-vcs

   Use the files checked in to git or mercurial as the starting list to include
   in an sdist, and then apply inclusions and exclusions :ref:`from pyproject.toml
   <pyproject_toml_sdist>`.

   This is the default for now, but we're planning to switch to ``--no-use-vcs``
   as the default in a future version.

.. option:: --no-use-vcs

   Create the sdist starting with only the files inside the installed module
   or package, along with any inclusions and exclusions defined in pyproject.toml.

   With this option, sdists from ``flit build`` are equivalent to those built
   by tools calling Flit as a backend, such as `build
   <https://pypa-build.readthedocs.io/en/stable/>`_.

.. _publish_cmd:

``flit publish``
----------------

.. program:: flit publish

Build a wheel and an sdist (tarball) from the package, and upload them to PyPI
or another repository.

.. option:: --format <format>

   Limit to publishing either ``wheel`` or ``sdist``.
   You should normally publish the two formats together.

.. option:: --setup-py
.. option:: --no-setup-py
.. option:: --use-vcs
.. option:: --no-use-vcs

   These options affecting what goes in the sdist are described for
   :ref:`build_cmd` above.

.. option:: --repository <repository>

   Name of a repository to upload packages to. Should match a section in
   ``~/.pypirc``. The default is ``pypi``.

.. option:: --pypirc <pypirc>

   The .pypirc config file to be used. The default is ``~/.pypirc``.

.. seealso:: :doc:`upload`

.. _install_cmd:

``flit install``
----------------

.. program:: flit install

Install the package on your system.

By default, the package is installed to the same Python environment that Flit
itself is installed in; use :option:`--python` or :envvar:`FLIT_INSTALL_PYTHON`
to override this.

If you don't have permission to modify the environment (e.g. the system Python
on Linux), Flit may do a user install instead. Use the :option:`--user` or
:option:`--env` flags to force this one way or the other, rather than letting
Flit guess.

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
   or ``none``. ``all`` and ``develop`` install the extras ``test``, ``doc``,
   and ``dev``. Default ``all``.

.. option:: --extras <extra[,extra,...]>

   Which named extra features to install dependencies for. Specify ``all`` to
   install all optional dependencies, or a comma-separated list of extras.
   Default depends on ``--deps``.

.. option:: --only-deps

   Install the dependencies of this package, but not the package itself.

   This can be useful for e.g. building a container image, where your own code
   is copied or mounted into the container at a later stage.

   .. versionadded:: 3.8

.. option:: --user

   Do a user-local installation. This is the default if flit is not in a
   virtualenv or conda env (if the environment's library directory is
   read-only and ``site.ENABLE_USER_SITE`` is true).

.. option:: --env

   Install into the environment - the opposite of :option:`--user`.
   This is the default in a virtualenv or conda env (if the environment's
   library directory is writable or ``site.ENABLE_USER_SITE`` is false).

.. option:: --python <path to python>

   Install for another Python, identified by the path of the python
   executable. Using this option, you can install a module for Python 2, for
   instance. See :envvar:`FLIT_INSTALL_PYTHON` if this option is not given.

   .. versionchanged:: 2.1
      Added :envvar:`FLIT_INSTALL_PYTHON` and use its value over the Python
      running Flit when an explicit :option:`--python` option is not given.

.. note::

   Flit calls pip to do the installation. You can set any of pip's options
   `using its environment variables
   <https://pip.pypa.io/en/stable/topics/configuration/#environment-variables>`__.

   When you use the :option:`--symlink` or :option:`--pth-file` options, pip
   is used to install dependencies. Otherwise, Flit builds a wheel and then
   calls pip to install that.

.. _init_cmd:

``flit init``
-------------

.. program:: flit init

Create a new ``pyproject.toml``  config file by prompting for information about
the module in the current directory.

Environment variables
---------------------

.. envvar:: FLIT_NO_NETWORK

   .. versionadded:: 0.10

   Setting this to any non-empty value will stop flit from making network
   connections (unless you explicitly ask to upload a package). This
   is intended for downstream packagers, so if you use this, it's up to you to
   ensure any necessary dependencies are installed.

.. envvar:: FLIT_ROOT_INSTALL

   By default, ``flit install`` will fail when run as root on POSIX systems,
   because installing Python modules systemwide is not recommended. Setting
   this to any non-empty value allows installation as root. It has no effect on
   Windows.

.. envvar:: FLIT_USERNAME
            FLIT_PASSWORD
            FLIT_INDEX_URL

   .. versionadded:: 0.11

   Set a username, password, and index URL for uploading packages.
   See :ref:`uploading packages with environment variables <upload_envvars>`
   for more information.
   
   Token-based upload to PyPI is supported. To upload using a PyPI token,
   set ``FLIT_USERNAME`` to ``__token__``, and ``FLIT_PASSWORD`` to the
   token value.

.. envvar:: FLIT_ALLOW_INVALID

   .. versionadded:: 0.13

   Setting this to any non-empty value tells Flit to continue if it detects
   invalid metadata, instead of failing with an error. Problems will still be
   reported in the logs, but won't cause Flit to stop.

   If the metadata is invalid, uploading the package to PyPI may fail. This
   environment variable provides an escape hatch in case Flit incorrectly
   rejects your valid metadata. If you need to use it and you believe your
   metadata is valid, please `open an issue <https://github.com/pypa/flit/issues>`__.

.. envvar:: FLIT_INSTALL_PYTHON

   .. versionadded:: 2.1

   .. program:: flit install

   Set a default Python interpreter for :ref:`install_cmd` to use when
   :option:`--python` is not specified. The value can be either an absolute
   path, or a command name (which will be found in ``PATH``). If this is unset
   or empty, the module is installed for the copy of Python that is running
   Flit.

.. envvar:: SOURCE_DATE_EPOCH

   To make reproducible builds, set this to a timestamp as a number of seconds
   since the start of the year 1970 in UTC, and document the value you used.
   On Unix systems, you can get a value for the current time by running::

       date +%s


   .. seealso::

      `The SOURCE_DATE_EPOCH specification
      <https://reproducible-builds.org/specs/source-date-epoch/>`__

