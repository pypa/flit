Release history
===============

Version Next
------------

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
