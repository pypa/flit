Release history
===============

Version 3.10.1
--------------

- The sdist of ``flit_core`` now includes the corresponding tests (:ghpull:`704`).
  These were missing in 3.10.

Version 3.10
------------

- ``flit publish`` can now use PyPI tokens stored in keyring (:ghpull:`649`),
  either project tokens with a 'username' like
  :samp:`pypi_token:project:{project_name}` (use the `normalised form of the
  name <https://packaging.python.org/en/latest/specifications/name-normalization/>`_)
  or user tokens (:samp:`pypi_token:user:{username}`).
- The ``--python`` option can now take the path of a virtualenv folder, as an
  alternative to a Python executable (:ghpull:`667`).
- Flit will work with current development versions of Pythona again (:ghpull:`684`).
- The ``flit`` command line package now requires Python 3.8 or above (:ghpulL:`660`).
  ``flit_core`` still works with Python 3.6 or above.
- The metadata in packages now has the names of optional dependency groups
  ("extras") normalised, complying with version 2.3 of the metadata standard
  (:ghpull:`676`, :ghpull:`697`).
- The ``flit`` command line package now depends on pip (:ghpull:`647`).
- Fix potential substitution of environment variables into passwords read from
  ``.pypirc`` files (:ghpull:`652`).
- A warning is now shown when building packages which specify the old
  ``flit.buildapi`` backend, which should be replaced by ``flit_core.buildapi``
  (:ghpull:`674`). It's a good idea to always set a maximum version for the
  build requirement, to protect against changes in future major versions of Flit.
- Avoid using the deprecated ``datetime.utcfromtimestamp()`` (:ghpull:`682`).
- Flit now has a ``SECURITY.md`` file in the Github repository (:ghpull:`665`).
- The tests for ``flit_core`` are no longer part of the installed package,
  reducing the size of the wheels (:ghpull:`691`).

Version 3.9
-----------

- New options :option:`flit build --use-vcs` and :option:`flit build --no-use-vcs`
  to enable & disable including all committed files in the sdist. For now
  ``--use-vcs`` is the default, but this is likely to change in a future
  version, to bring ``flit build`` in line with standard build frontends like
  ``python -m build`` (:ghpull:`625`).
- Sdist file names, and the name of the top-level folder in an sdist, are now
  normalised, in accordance with :pep:`625` (:ghpull:`628`).
- A statically defined version number can now be parsed from files called
  ``version.py``, ``_version.py`` or ``__version__.py`` inside a package, as well
  as from ``__init__.py``, so executing code is required in fewer cases
  (:ghpull:`630`).
- Fix setting the flag for regular files in zip metadata (:ghpull:`639`).
- The timestamp embedded in the gzip wrapper for sdists now defaults to a fixed
  date, so building an sdist twice on the same machine should produce identical
  results, even without any special steps (:ghpull:`635`). Setting
  :envvar:`SOURCE_DATE_EPOCH` is still recommended for properly
  :doc:`reproducible builds <reproducible>`.

Version 3.8
-----------

- A project name containing hyphens is now automatically translated to use
  underscores for the import name (:ghpull:`566`).
- New option :option:`flit install --only-deps` to install the dependencies of
  the package, but not the package itself.
- Add support for recursive globbing (``**``) in sdist includes and excludes
  (:ghpull:`550`).
- Python's bytecode cache files (``__pycache__`` folders and ``.pyc`` files)
  are now always excluded from sdists (:ghpull:`581`).
- Use tomllib in Python 3.11, rather than tomli (:ghpull:`573`, :ghpull:`604`).
- Fix crash when unable to get a password from ``keyring`` (:ghpull:`567`).
- Fix including modified files in sdist when using Mercurial (:ghpull:`541`).
- Fix for some cases of determining whether a package supports Python 2 or not
  (:ghpull:`593`).
- Fix parsing version number from code using multiple assignments (:ghpull:`474`).
- Document how to use a PyPI token with :envvar:`FLIT_PASSWORD` (:ghpull:`602`).
- Fix link to information about environment variables for pip (:ghpull:`576`).
- Link to the docs for the latest stable version in package metadata
  (:ghpull:`589`).
- Remove a mention of the ``toml`` package, which is no longer needed, from the
  :doc:`development` page (:ghpull:`601`).
- The :doc:`bootstrap <bootstrap>` install script for ``flit_core`` accepts a
  new ``--install-root`` option.
- Ensure the license file is included in packages on PyPI (:ghpull:`603`).

Version 3.7.1
-------------

- Fix building packages which need execution to get the version number,
  and have a relative import in ``__init__.py`` (:ghpull:`531`).

Version 3.7
-----------

- Support for :ref:`external data files <pyproject_toml_external_data>` such
  as man pages or Jupyter extension support files (:ghpull:`510`).
- Project names are now lowercase in wheel filenames and ``.dist-info`` folder
  names, in line with the specifications (:ghpull:`498`).
- Improved support for :doc:`bootstrapping <bootstrap>` a Python environment,
  e.g. for downstream packagers (:ghpull:`511`). ``flit_core.wheel`` is usable
  with ``python -m`` to create wheels before the `build <https://pypi.org/project/build/>`_
  tool is available, and ``flit_core`` sdists also include a script to install
  itself from a wheel before `installer <https://pypi.org/project/installer/>`_
  is available.
- Use newer importlib APIs, fixing some deprecation warnings (:ghpull:`499`).

Version 3.6
-----------

- ``flit_core`` now bundles the `tomli <https://pypi.org/project/tomli/>`_ TOML
  parser library (version 1.2.3) to avoid a circular dependency between
  ``flit_core`` and ``tomli`` (:ghpull:`492`). This means ``flit_core`` now has
  no dependencies except Python itself, both at build time and at runtime,
  simplifying :doc:`bootstrapping <bootstrap>`.

Version 3.5.1
-------------

- Fix development installs with ``flit install --symlink`` and ``--pth-file``,
  which were broken in 3.5.0, especially for packages using a ``src`` folder
  (:ghpull:`472`).

Version 3.5
-----------

- You can now use Flit to distribute a module or package inside a namespace
  package (as defined by :pep:`420`). To do this, specify the import name of the
  concrete, inner module you are packaging - e.g. ``name = "sphinxcontrib.foo"``
  - either in the ``[project]`` table, or under ``[tool.flit.module]`` if you
  want to use a different name on PyPI (:ghpull:`468`).
- Flit no longer generates a ``setup.py`` file in sdists (``.tar.gz`` packages)
  by default (:ghpull:`462`). Modern packaging tools don't need this. You can
  use the ``--setup-py`` flag to keep adding it for now, but this will probably
  be removed at some point in the future.
- Fixed how ``flit init`` handles authors' names with non-ASCII characters
  (:ghpull:`460`).
- When ``flit init`` generates a LICENSE file, the new ``pyproject.toml`` now
  references it (:ghpull:`467`).

Version 3.4
-----------

- Python 3.6 or above is now required, both for ``flit`` and ``flit_core``.
- Add a ``--setup-py`` option to ``flit build`` and ``flit publish``, and a
  warning when neither this nor ``--no-setup-py`` are specified (:ghpull:`431`).
  A future version will stop generating ``setup.py`` files in sdists by default.
- Add support for standardised editable installs - ``pip install -e`` -
  according to :pep:`660` (:ghpull:`400`).
- Add a ``--pypirc`` option for ``flit publish`` to specify an alternative path
  to a ``.pypirc`` config file describing package indexes (:ghpull:`434`).
- Fix installing dependencies specified in a ``[project]`` table (:ghpull:`433`).
- Fix building wheels when ``SOURCE_DATE_EPOCH`` (see :doc:`reproducible`) is
  set to a date before 1980 (:ghpull:`448`).
- Switch to using the `tomli <https://pypi.org/project/tomli/>`_ TOML parser,
  in common with other packaging projects (:ghpull:`438`).
  This supports TOML version 1.0.
- Add a document on :doc:`bootstrap` (:ghpull:`441`).

Version 3.3
-----------

- ``PKG-INFO`` files in sdists are now generated the same way as ``METADATA`` in
  wheels, fixing some issues with sdists (:ghpull:`410`).
- ``flit publish`` now sends SHA-256 hashes, fixing uploads to GitLab package
  repositories (:ghpull:`416`).
- The ``[project]`` metadata table from :pep:`621` is now fully supported and
  :ref:`documented <pyproject_toml_project>`. Projects using this can now
  specify ``requires = ["flit_core >=3.2,<4"]`` in the ``[build-system]`` table.

Version 3.2
-----------

- Experimental support for specifying metadata in a ``[project]`` table in
  ``pyproject.toml`` as specified by :pep:`621` (:ghpull:`393`). If you try
  using this, please specify ``requires = ["flit_core >=3.2.0,<3.3"]`` in the
  ``[build-system]`` table for now, in case it needs to change for the next
  release.
- Fix writing METADATA file with multi-line information in certain fields
  such as ``Author`` (:ghpull:`402`).
- Fix building wheel when a directory such as LICENSES appears in the project
  root directory (:ghpull:`401`).

Version 3.1
-----------

- Update handling of names & version numbers in wheel filenames and
  ``.dist-info`` folders in line with changes in the specs (:ghpull:`395`).
- Switch from the deprecated ``pytoml`` package to ``toml`` (:ghpull:`378`).
- Fix specifying backend-path in ``pyproject.toml`` for flit-core (as a list
  instead of a string).

Version 3.0
-----------

Breaking changes:

- Projects must now provide Flit with information in ``pyproject.toml`` files,
  not the older ``flit.ini`` format (:ghpull:`338`).
- ``flit_core`` once again requires Python 3 (>=3.4). Packages that support
  Python 2 can still be built by ``flit_core`` 2.x, but can't rely on new
  features (:ghpull:`342`).
- The deprecated ``flit installfrom`` command was removed (:ghpull:`334`).
  You can use ``pip install git+https://github.com/...`` instead.

Features and fixes:

- Fix building sdists from a git repository with non-ASCII characters in
  filenames (:ghpull:`346`).
- Fix identifying the version number when the code contains a subscript
  assignment before ``__version__ =`` (:ghpull:`348`).
- Script entry points can now use a class method (:ghpull:`359`).
- Set suitable permission bits on metadata files in wheels (:ghpull:`256`).
- Fixed line endings in the ``RECORD`` file when installing on Windows
  (:ghpull:`368`).
- Support for recording the source of local installations, as in :pep:`610`
  (:ghpull:`335`).
- ``flit init`` will check for a README in the root of the project and
  automatically set it as ``description-file`` (:ghpull:`337`).
- Pygments is not required for checking reStructuredText READMEs (:ghpull:`357`).
- Packages where the version number can be recognised without executing their
  code don't need their dependencies installed to build, which should make them
  build faster (:ghpull:`361`).
- Ensure the installed ``RECORD`` file is predictably ordered (:ghpull:`366`).

Version 2.3
-----------

- New projects created with :ref:`init_cmd` now declare that they require
  ``flit_core >=2,<4`` (:ghpull:`328`). Any projects using ``pyproject.toml``
  (not ``flit.ini``) should be compatible with flit 3.x.
- Fix selecting files from a git submodule to include in an sdist
  (:ghpull:`324`).
- Fix checking classifiers when no writeable cache directory is available
  (:ghpull:`319`).
- Better errors when trying to install to a mis-spelled or missing Python
  interpreter (:ghpull:`331`).
- Fix specifying ``--repository`` before ``upload`` (:ghpull:`322`). Passing the
  option like this is deprecated, and you should now pass it after ``upload``.
- Documentation improvements (:ghpull:`327`, :ghpull:`318`, :ghpull:`314`)

Version 2.2
-----------

- Allow underscores in package names with Python 2 (:ghpull:`305`).
- Add a ``--no-setup-py`` option to build sdists without a backwards-compatible
  ``setup.py`` file (:ghpull:`311`).
- Fix the generated ``setup.py`` file for packages using a ``src/`` layout
  (:ghpull:`303`).
- Fix detecting when more than one file matches the module name specified
  (:ghpull:`307`).
- Fix installing to a venv on Windows with the ``--python`` option
  (:ghpull:`300`).
- Don't echo the command in scripts installed with ``--symlink`` or
  ``--pth-file`` on Windows (:ghpull:`310`).
- New ``bootstrap_dev.py`` script to set up a development installation of Flit
  from the repository (:ghpull:`301`, :ghpull:`306`).

Version 2.1
-----------

- Use compression when adding files to wheels.
- Added the :envvar:`FLIT_INSTALL_PYTHON` environment variable (:ghpull:`295`),
  to configure flit to always install into a Python other than the one it's
  running on.
- ``flit_core`` uses the ``intreehooks`` shim package to load its bootstrapping
  backend, until a released version of pip supports the standard
  ``backend-path`` mechanism.

Version 2.0
-----------

Flit 2 is a major architecture change. The ``flit_core`` package now provides
a :pep:`517` backend for building packages, while ``flit`` is a
:doc:`command line interface <cmdline>` extending that.

The build backend works on Python 2, so tools like pip should be able to install
packages built with flit from source on Python 2.
The ``flit`` command requires Python 3.5 or above.
You will need to change the build-system table in your ``pyproject.toml`` file
to look like this:

.. code-block:: toml

    [build-system]
    requires = ["flit_core >=2,<4"]
    build-backend = "flit_core.buildapi"

Other changes include:

- Support for storing your code under a ``src/`` folder (:ghpull:`260`).
  You don't need to change any configuration if you do this.
- Options to control what files are included in an sdist - see
  :ref:`pyproject_toml_sdist` for the details.
- Requirements can specify a URL 'direct reference', as an alternative to a
  version number, with the syntax defined in :pep:`440`:
  ``requests @ https://example.com/requests-2.22.0.tar.gz``.
- Fix the shebang of scripts installed with the ``--python`` option and the
  ``--symlink`` flag (:ghpull:`286`).
- Installing with ``--deps develop`` now installs normal dependencies
  as well as development dependencies.
- Author email is no longer required in the metadata table (:ghpull:`289`).
- More error messages are now shown without a traceback (:ghpull:`254`)

Version 1.3
-----------

- Fix for building sdists from a subdirectory in a Mercurial repository
  (:ghpull:`233`).
- Fix for getting the docstring and version from modules defining their encoding
  (:ghpull:`239`).
- Fix for installing packages with ``flit installfrom`` (:ghpull:`221`).
- Packages with requirements no longer get a spurious ``Provides-Extra: .none``
  metadata entry (:ghissue:`228`).
- Better check of whether ``python-requires`` includes any Python 2 version
  (:ghpull:`232`).
- Better check of home page URLs in ``flit init`` (:ghpull:`230`).
- Better error message when the description file is not found (:ghpull:`234`).
- Updated a help message to refer to ``pyproject.toml`` (:ghpull:`240`).
- Improve tests of ``flit init`` (:ghpull:`229`).

Version 1.2.1
-------------

- Fix for installing packages with ``flit install``.
- Make ``requests_download`` an extra dependency, to avoid a circular build
  dependency. To use ``flit installfrom``, you can install with
  ``pip install flit[installfrom]``. Note that the ``installfrom`` subcommand
  is deprecated, as it will soon be possible to use pip to install Flit projects
  directly from a VCS URL.

Version 1.2
-----------

- Fixes for packages specifying ``requires-extra``: sdists should now work, and
  environment markers can be used together with ``requires-extra``.
- Fix running ``flit installfrom`` without a config file present in the
  working directory.
- The error message for a missing or empty docstring tells you what file
  the docstring should be in.
- Improvements to documentation on version selectors for requirements.

Version 1.1
-----------

- Packages can now have 'extras', specified as ``requires-extra`` in the
  :doc:`pyproject.toml file <pyproject_toml>`. These are additional dependencies
  for optional features.
- The ``home-page`` metadata field is no longer required.
- Additional project URLs are now validated.
- ``flit -V`` is now equivalent to ``flit --version``.
- Various improvements to documentation.

Version 1.0
-----------

- The description file may now be written in reStructuredText, Markdown or
  plain text. The file extension should indicate which of these formats it is
  (``.rst``, ``.md`` or ``.txt``). Previously, only reStructuredText was
  officially supported.
- Multiple links (e.g. documentation, bug tracker) can now be specified in a
  new :ref:`[tool.flit.metadata.urls] section <pyproject_toml_urls>` of
  ``pyproject.toml``.
- Dependencies are now correctly installed to the target Python when you use
  the ``--symlink`` or ``--pth-file`` options.
- Dependencies are only installed to the Python where Flit is running if
  it fails to get the docstring and version number without them.
- The commands deprecated in 0.13—``flit wheel``, ``flit sdist`` and
  ``flit register``—have been removed.

Although version 1.0 sounds like a milestone, there's nothing that makes this
release especially significant. It doesn't represent a step change in stability
or completeness. Flit has been gradually maturing for some time, and I chose
this point to end the series of 0.x version numbers.

Version 0.13
------------

- Better validation of several metadata fields (``dist-name``, ``requires``,
  ``requires-python``, ``home-page``), and of the version number.
- New :envvar:`FLIT_ALLOW_INVALID` environment variable to ignore validation
  failures in case they go wrong.
- The list of valid classifiers is now fetched from Warehouse (https://pypi.org),
  rather than the older https://pypi.python.org site.
- Deprecated ``flit wheel`` and ``flit sdist`` subcommands: use
  :ref:`build_cmd`.
- Deprecated ``flit register``: you can no longer register a package separately
  from uploading it.

Version 0.12.3
--------------

- Fix building and installing packages with a ``-`` in the distribution name.
- Fix numbering in README.

Version 0.12.2
--------------

- New tool to convert ``flit.ini`` to ``pyproject.toml``::

      python3 -m flit.tomlify

- Use the PAX tar format for sdists, as specified by PEP 517.

Version 0.12.1
--------------

- Restore dependency on ``zipfile36`` backport package.
- Add some missing options to documentation of ``flit install`` subcommand.
- Rearrange environment variables in the docs.

Version 0.12
------------

- Switch the config to ``pyproject.toml`` by default instead of ``flit.ini``,
  and implement the PEP 517 API.
- A new option ``--pth-file`` allows for development installation on Windows
  (where ``--symlink`` usually won't work).
- Normalise file permissions in the zip file, making builds more reproducible
  across different systems.
- Sdists (.tar.gz packages) can now also be reproducibly built by setting
  :envvar:`SOURCE_DATE_EPOCH`.
- For most modules, Flit can now extract the version number and docstring
  without importing it. It will still fall back to importing where getting
  these from the AST fails.
- ``flit build`` will build the wheel from the sdist, helping to ensure that
  files aren't left out of the sdist.
- All list fields in the INI file now ignore blank lines (``requires``,
  ``dev-requires``, ``classifiers``).
- Fix the path separator in the ``RECORD`` file of a wheel built on Windows.
- Some minor fixes to building reproducible wheels.
- If building a wheel fails, the temporary file created will be cleaned up.
- Various improvements to docs and README.

Version 0.11.4
--------------

- Explicitly open various files as UTF-8, rather than relying on locale
  encoding.
- Link to docs from README.
- Better test coverage, and a few minor fixes for problems revealed by tests.

Version 0.11.3
--------------

- Fixed a bug causing failed uploads when the password is entered in the
  terminal.

Version 0.11.2
--------------

- A couple of behaviour changes when uploading to warehouse.

Version 0.11.1
--------------

- Fixed a bug when you use flit to build an sdist from a subdirectory inside a
  VCS checkout. The VCS is now correctly detected.
- Fix the rst checker for newer versions of docutils, by upgrading the bundled
  copy of readme_renderer.

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
- Support for entry points.
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
