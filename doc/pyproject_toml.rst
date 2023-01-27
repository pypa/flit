The pyproject.toml config file
==============================

This file lives next to the module or package.

.. note::

   Older version of Flit (up to 0.11) used a :doc:`flit.ini file <flit_ini>` for
   similar information. These files no longer work with Flit 3 and above.

   Run ``python3 -m flit.tomlify`` to convert a ``flit.ini`` file to
   ``pyproject.toml``.

Build system section
--------------------

This tells tools like pip to build your project with flit. It's a standard
defined by PEP 517. For any new project using Flit, it will look like this:

.. code-block:: toml

    [build-system]
    requires = ["flit_core >=3.2,<4"]
    build-backend = "flit_core.buildapi"

Version constraints:

- For now, all packages should specify ``<4``, so they won't be impacted by
  changes in the next major version.
- :ref:`pyproject_toml_project` requires ``flit_core >=3.2``
- :ref:`pyproject_old_metadata` requires ``flit_core >=2,<4``
- The older :doc:`flit.ini file <flit_ini>` requires ``flit_core <3``.
- TOML features new in version 1.0 require ``flit_core >=3.4``.
- ``flit_core`` 3.3 is the last version supporting Python 3.4 & 3.5. Packages
  supporting these Python versions can only use `TOML v0.5
  <https://toml.io/en/v0.5.0>`_.
- Only ``flit_core`` 2.x can build packages on Python 2, so packages still
  supporting Python 2 cannot use new-style metadata (the ``[project]`` table).

.. _pyproject_toml_project:

New style metadata
------------------

.. versionadded:: 3.2

The new standard way to specify project metadata is in a ``[project]`` table,
as defined by :pep:`621`. Flit works for now with either this or the older
``[tool.flit.metadata]`` table (:ref:`described below <pyproject_old_metadata>`),
but it won't allow you to mix them.

A simple ``[project]`` table might look like this:

.. code-block:: toml

    [project]
    name = "astcheck"
    authors = [
        {name = "Thomas Kluyver", email = "thomas@kluyver.me.uk"},
    ]
    readme = "README.rst"
    classifiers = [
        "License :: OSI Approved :: MIT License",
    ]
    requires-python = ">=3.5"
    dynamic = ["version", "description"]

The allowed fields are:

name
  The name your package will have on PyPI. This field is required. For Flit,
  this name, with any hyphens replaced by underscores, is also the default value
  of the import name (see :ref:`pyproject_module` if that needs to be
  different).

  .. versionchanged:: 3.8
     Hyphens in the project name are now translated to underscores for the
     import name.
version
  Version number as a string. If you want Flit to get this from a
  ``__version__`` attribute, leave it out of the TOML config and include
  "version" in the ``dynamic`` field.
description
  A one-line description of your project. If you want Flit to get this from
  the module docstring, leave it out of the TOML config and include
  "description" in the ``dynamic`` field.
readme
  A path (relative to the .toml file) to a file containing a longer description
  of your package to show on PyPI. This should be written in `reStructuredText
  <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_, Markdown or
  plain text, and the filename should have the appropriate extension
  (``.rst``, ``.md`` or ``.txt``). Alternatively, ``readme`` can be a table with
  either a ``file`` key (a relative path) or a ``text`` key (literal text), and
  an optional ``content-type`` key (e.g. ``text/x-rst``).
requires-python
  A version specifier for the versions of Python this requires, e.g. ``~=3.3`` or
  ``>=3.3,<4``, which are equivalents.
license
  A table with either a ``file`` key (a relative path to a license file) or a
  ``text`` key (the license text).
authors
  A list of tables with ``name`` and ``email`` keys (both optional) describing
  the authors of the project.
maintainers
  Same format as authors.
keywords
  A list of words to help with searching for your package.
classifiers
  A list of `Trove classifiers <https://pypi.python.org/pypi?%3Aaction=list_classifiers>`_.
  Add ``Private :: Do Not Upload`` into the list to prevent a private package
  from being uploaded to PyPI by accident.
dependencies & optional-dependencies
  See :ref:`pyproject_project_dependencies`.
urls
  See :ref:`pyproject_project_urls`.
scripts & gui-scripts
  See :ref:`pyproject_project_scripts`.
entry-points
  See :ref:`pyproject_project_entrypoints`.
dynamic
  A list of field names which aren't specified here, for which Flit should
  find a value at build time. Only "version" and "description" are accepted.

.. _pyproject_project_dependencies:

Dependencies
~~~~~~~~~~~~

The ``dependencies`` field is a list of other packages from PyPI that this
package needs. Each package may be followed by a version specifier like
``>=4.1``, and/or an `environment marker`_
after a semicolon. For example:

  .. code-block:: toml

      dependencies = [
          "requests >=2.6",
          "configparser; python_version == '2.7'",
      ]

The ``[project.optional-dependencies]`` table contains lists of packages needed
for every optional feature. The requirements are specified in the same format as
for ``dependencies``. For example:

  .. code-block:: toml

      [project.optional-dependencies]
      test = [
          "pytest >=2.7.3",
          "pytest-cov",
      ]
      doc = ["sphinx"]

You can call these optional features anything you want, although ``test`` and
``doc`` are common ones. You specify them for installation in square brackets
after the package name or directory, e.g. ``pip install '.[test]'``.

.. _pyproject_project_urls:

URLs table
~~~~~~~~~~

Your project's page on `pypi.org <https://pypi.org/>`_ can show a number of
links. You can point people to documentation or a bug tracker, for example.

This section is called ``[project.urls]`` in the file. You can use
any names inside it. Here it is for flit:

.. code-block:: toml

  [project.urls]
  Documentation = "https://flit.pypa.io"
  Source = "https://github.com/pypa/flit"

.. _pyproject_project_scripts:

Scripts section
~~~~~~~~~~~~~~~

This section is called ``[project.scripts]`` in the file.
Each key and value describes a shell command to be installed along with
your package. These work like setuptools 'entry points'. Here's the section
for flit:

.. code-block:: toml

    [project.scripts]
    flit = "flit:main"


This will create a ``flit`` command, which will call the function ``main()``
imported from :mod:`flit`.

A similar table called ``[project.gui-scripts]`` defines commands which launch
a GUI. This only makes a difference on Windows, where GUI scripts are run
without a console.

.. _pyproject_project_entrypoints:

Entry points sections
~~~~~~~~~~~~~~~~~~~~~

You can declare `entry points <http://entrypoints.readthedocs.io/en/latest/>`_
using sections named :samp:`[project.entry-points.{groupname}]`. E.g. to
provide a pygments lexer from your package:

.. code-block:: toml

    [project.entry-points."pygments.lexers"]
    dogelang = "dogelang.lexer:DogeLexer"

In each ``package:name`` value, the part before the colon should be an
importable module name, and the latter part should be the name of an object
accessible within that module. The details of what object to expose depend on
the application you're extending.

If the group name contains a dot, it must be quoted (``"pygments.lexers"``
above). Script entry points are defined in :ref:`scripts tables
<pyproject_project_scripts>`, so you can't use the group names
``console_scripts`` or ``gui_scripts`` here.

.. _pyproject_module:

Module section
~~~~~~~~~~~~~~

If your package will have different names for installation and import,
you should specify the install (PyPI) name in the ``[project]`` table
(:ref:`see above <pyproject_toml_project>`), and the import name in a
``[tool.flit.module]`` table:

.. code-block:: toml

    [project]
    name = "pynsist"
    # ...

    [tool.flit.module]
    name = "nsist"

Flit looks for the source of the package by its import name. The source may be
located either in the directory that holds the ``pyproject.toml`` file, or in a
``src/`` subdirectory.

.. _pyproject_old_metadata:

Old style metadata
------------------

Flit's older way to specify metadata is in a ``[tool.flit.metadata]`` table,
along with ``[tool.flit.scripts]`` and ``[tool.flit.entrypoints]``, described
below. This is still recognised for now, but you can't mix it with
:ref:`pyproject_toml_project`.

There are three required fields:

module
  The name of the module/package, as you'd use in an import statement.
author
  Your name
author-email
  Your email address

e.g. for flit itself

.. code-block:: toml

    [tool.flit.metadata]
    module = "flit"
    author = "Thomas Kluyver"
    author-email = "thomas@kluyver.me.uk"

.. versionchanged:: 1.1

   ``home-page`` was previously required.

The remaining fields are optional:

home-page
  A URL for the project, such as its Github repository.
requires
  A list of other packages from PyPI that this package needs. Each package may
  be followed by a version specifier like ``(>=4.1)`` or ``>=4.1``, and/or an
  `environment marker`_
  after a semicolon. For example:

  .. code-block:: toml

      requires = [
          "requests >=2.6",
          "configparser; python_version == '2.7'",
      ]

requires-extra
  Lists of packages needed for every optional feature. The requirements
  are specified in the same format as for ``requires``. The requirements of
  the two reserved extras ``test`` and ``doc`` as well as the extra ``dev``
  are installed by ``flit install``. For example:

  .. code-block:: toml

      [tool.flit.metadata.requires-extra]
      test = [
          "pytest >=2.7.3",
          "pytest-cov",
      ]
      doc = ["sphinx"]

  .. versionadded:: 1.1

description-file
  A path (relative to the .toml file) to a file containing a longer description
  of your package to show on PyPI. This should be written in `reStructuredText
  <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_, Markdown or
  plain text, and the filename should have the appropriate extension
  (``.rst``, ``.md`` or ``.txt``).
classifiers
  A list of `Trove classifiers <https://pypi.python.org/pypi?%3Aaction=list_classifiers>`_.
  Add ``Private :: Do Not Upload`` into the list to prevent a private package
  from uploading on PyPI by accident.
requires-python
  A version specifier for the versions of Python this requires, e.g. ``~=3.3`` or
  ``>=3.3,<4`` which are equivalents.
dist-name
  If you want your package's name on PyPI to be different from the importable
  module name, set this to the PyPI name.
keywords
  Comma separated list of words to help with searching for your package.
license
  The name of a license, if you're using one for which there isn't a Trove
  classifier. It's recommended to use Trove classifiers instead of this in
  most cases.
maintainer, maintainer-email
  Like author, for if you've taken over a project from someone else.

Here was the metadata section from flit using the older style:

.. code-block:: toml

    [tool.flit.metadata]
    module="flit"
    author="Thomas Kluyver"
    author-email="thomas@kluyver.me.uk"
    home-page="https://github.com/pypa/flit"
    requires=[
        "flit_core >=2.2.0",
        "requests",
        "docutils",
        "tomli",
        "tomli-w",
    ]
    requires-python=">=3.6"
    description-file="README.rst"
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]

.. _pyproject_toml_urls:

URLs subsection
~~~~~~~~~~~~~~~

Your project's page on `pypi.org <https://pypi.org/>`_ can show a number of
links, in addition to the ``home-page`` URL described above. You can
point people to documentation or a bug tracker, for example.

This section is called ``[tool.flit.metadata.urls]`` in the file. You can use
any names inside it. Here it is for flit:

.. code-block:: toml

  [tool.flit.metadata.urls]
  Documentation = "https://flit.pypa.io"

.. versionadded:: 1.0

.. _pyproject_toml_scripts:

Scripts section
~~~~~~~~~~~~~~~

A ``[tool.flit.scripts]`` table can be used along with ``[tool.flit.metadata]``.
It is in the same format as the newer ``[project.scripts]`` table
:ref:`described above <pyproject_project_scripts>`.

Entry points sections
~~~~~~~~~~~~~~~~~~~~~

``[tool.flit.entrypoints]`` tables can be used along with ``[tool.flit.metadata]``.
They are in the same format as the newer ``[project.entry-points]`` tables
:ref:`described above <pyproject_project_entrypoints>`.

.. _pyproject_toml_sdist:

Sdist section
-------------

.. versionadded:: 2.0

With no configuration, Flit can make an sdist with everything it needs
to build and install your module: the package contents (including non-Python
data files, but not ``.pyc`` bytecode files), your ``pyproject.toml`` file,
the readme & license files given in the metadata, and the :ref:`external data
folder <pyproject_toml_external_data>` if you specified that.

If you want more control, you can give lists of paths or glob patterns as
``include`` and ``exclude`` in this section. For example:

.. code-block:: toml

    [tool.flit.sdist]
    include = ["doc/"]
    exclude = ["doc/*.html"]

These paths:

- Always use ``/`` as a separator (POSIX style)
- Must be relative paths from the directory containing ``pyproject.toml``
- Cannot go outside that directory (no ``../`` paths)
- Cannot contain control characters or ``<>:"\\``
- Can refer to directories, in which case they include everything under the
  directory, including subdirectories
- Should match the case of the files they refer to, as case-insensitive matching
  is platform dependent

.. versionchanged:: 3.8
   Include and exclude patterns can now use recursive glob patterns (``**``).

Exclusions have priority over inclusions. Bytecode is excluded by default and cannot
be included.

Including files committed in git/hg
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you use :ref:`build_cmd` or :ref:`publish_cmd`, you can also make sdists with
the files which are committed in version control (git or hg). This is a shortcut
to e.g. include documentation source files, but not built HTML or PDF
documentation. The include and exclude patterns are then applied on top of this
list.

For now, including files from version control is the default for :ref:`build_cmd`
and :ref:`publish_cmd`, and can be disabled with ``--no-use-vcs``. The default
will switch in a future version.

Using ``flit_core`` as a backend to other tools such as `build
<https://pypa-build.readthedocs.io/en/latest/>`_ never gets the list of files
for the sdist from version control.

.. _pyproject_toml_external_data:

External data section
---------------------

.. versionadded:: 3.7

Data files which your code will use should go inside the Python package folder.
Flit will package these with no special configuration.

However, sometimes it's useful to package external files for system integration,
such as man pages or files defining a Jupyter extension. To do this, arrange
the files within a directory such as ``data``, next to your ``pyproject.toml``
file, and add a section like this:

.. code-block:: toml

    [tool.flit.external-data]
    directory = "data"

Paths within this directory are typically installed to corresponding paths under
a prefix (such as a virtualenv directory). E.g. you might save a man page for a
script as ``(data)/share/man/man1/foo.1``.

Whether these files are detected by the systems they're meant to integrate with
depends on how your package is installed and how those systems are configured.
For instance, installing in a virtualenv usually doesn't affect anything outside
that environment. Don't rely on these files being picked up unless you have
close control of how the package will be installed.

If you install a package with ``flit install --symlink``, a symlink is made
for each file in the external data directory. Otherwise (including development
installs with ``pip install -e``), these files are copied to their destination,
so changes here won't take effect until you reinstall the package.

.. note::

   For users coming from setuptools: external data corresponds to setuptools'
   ``data_files`` parameter, although setuptools offers more flexibility.

.. _environment marker: https://www.python.org/dev/peps/pep-0508/#environment-markers
