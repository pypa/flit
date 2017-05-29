Release history
===============

Version 0.11
------------

- Flit can now build sdists (tarballs) and upload them to PyPI, if your code is
  in a git or mercurial repository. There are new commands:

  - ``flit build`` builds both a wheel and an sdist.
  - ``flit publish`` builds and uploads a wheel and an sdist.

- Smarter ways of getting the information needed for upload:

  - If you have the `keyring <https://github.com/jaraco/keyring>`_ package
    installed, flit can use it to store your password, rather than keeping it
    in plain text in ``~/.pypirc``.
  - If ``~/.pypirc`` does not already exist, and you are prompted for your
    username, flit will write it into that file.
  - You can provide the information as environment variables:
    :envvar:`FLIT_USERNAME`, :envvar:`FLIT_PASSWORD` and :envvar:`FLIT_INDEX_URL`.
    Use this to upload packages from a CI service, for instance.

- Include 'LICENSE' or 'COPYING' files in wheels.
- Fix for ``flit install --symlink`` inside a virtualenv.


Version 0.10
------------

- Downstream packagers can use the :envvar:`FLIT_NO_NETWORK` environment
  variable to stop flit downloading data from the network.

Version 0.9
-----------

- ``flit install`` and ``flit installfrom`` now take an optional ``--python`` argument,
  with the path to the Python executable you want to install it for.
  Using this, you can install modules to Python 2.
- Installing a module normally (without ``--symlink``) builds a wheel and uses
  pip to install it, which should work better in some corner cases.

Version 0.8
-----------

- A new ``flit installfrom`` subcommand to install a project from a source
  archive, such as from Github.
- :doc:`Reproducible builds <reproducible>` - you can produce byte-for-byte
  identical wheels.
- A warning for non-canonical version numbers according to `PEP 440
  <https://www.python.org/dev/peps/pep-0440/>`__.
- Fix for installing projects on Windows.
- Better error message when module docstring is only whitespace.

Version 0.7
-----------

- A new ``dev-requires`` field in the config file for development requirements,
  used when doing ``flit install``.
- Added a ``--deps`` option for ``flit install`` to control which dependencies
  are installed.
- Flit can now be invoked with ``python -m flit``.

Version 0.6
-----------

- ``flit install`` now ensures requirements specified in ``flit.ini`` are
  installed, using pip.
- If you specify a description file, flit now warns you if it's not valid
  reStructuredText (since invalid reStructuredText is treated as plain text on
  PyPI).
- Improved the error message for mis-spelled keys in ``flit.ini``.

Version 0.5
-----------

- A new ``flit init`` command to quickly define the essential basic metadata
  for a package.
- Support for :doc:`entrypoints`.
- A new ``flit register`` command to register a package without uploading it,
  for when you want to claim a name before you're ready to release.
- Added a ``--repository`` option for specifying an alternative PyPI instance.
- Added a ``--debug`` flag to show debug-level log messages.
- Better error messages when the module docstring or ``__version__`` is missing.

Version 0.4
-----------

- Users can now specify ``dist-name`` in the config file if they need to use
  different names on PyPI and for imports.
- Classifiers are now checked against a locally cached list of valid
  classifiers.
- Packages can be locally installed into environments for development.
- Local installation now creates a PEP 376 ``.dist-info`` folder instead of
  ``.egg-info``.
