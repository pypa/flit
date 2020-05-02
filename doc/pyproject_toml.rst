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
defined by PEP 517. For any project using Flit, it will look like this:

.. code-block:: toml

    [build-system]
    requires = ["flit_core >=2,<4"]
    build-backend = "flit_core.buildapi"

Metadata section
----------------

This section is called ``[tool.flit.metadata]`` in the file.
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
  `environment marker
  <https://www.python.org/dev/peps/pep-0345/#environment-markers>`_
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

Here's the full metadata section from flit itself:

.. code-block:: toml

    [tool.flit.metadata]
    module="flit"
    author="Thomas Kluyver"
    author-email="thomas@kluyver.me.uk"
    home-page="https://github.com/takluyver/flit"
    requires=[
        "flit_core>=2.2.0",
        "requests",
        "docutils",
        "pytoml",
        "zipfile36; python_version in '3.3 3.4 3.5'",
    ]
    requires-python=">=3.5"
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
links, in addition to the required ``home-page`` URL described above. You can
point people to documentation or a bug tracker, for example.

This section is called ``[tool.flit.metadata.urls]`` in the file. You can use
any names inside it. Here it is for flit:

.. code-block:: toml

  [tool.flit.metadata.urls]
  Documentation = "https://flit.readthedocs.io/en/latest/"

.. versionadded:: 1.0

.. _pyproject_toml_scripts:

Scripts section
---------------

This section is called ``[tool.flit.scripts]`` in the file.
Each key and value describes a shell command to be installed along with
your package. These work like setuptools 'entry points'. Here's the section
for flit:

.. code-block:: toml

    [tool.flit.scripts]
    flit = "flit:main"


This will create a ``flit`` command, which will call the function ``main()``
imported from :mod:`flit`.

Entry points sections
---------------------

You can declare `entry points <http://entrypoints.readthedocs.io/en/latest/>`_
using sections named :samp:`[tool.flit.entrypoints.{groupname}]`. E.g. to
provide a pygments lexer from your package:

.. code-block:: toml

    [tool.flit.entrypoints."pygments.lexers"]
    dogelang = "dogelang.lexer:DogeLexer"

In each ``package:name`` value, the part before the colon should be an
importable module name, and the latter part should be the name of an object
accessible within that module. The details of what object to expose depend on
the application you're extending.

.. _pyproject_toml_sdist:

Sdist section
-------------

.. versionadded:: 2.0

When you use :ref:`build_cmd` or :ref:`publish_cmd`, Flit builds an sdist
(source distribution) tarball containing the files that are checked into version
control (git or mercurial). If you want more control, or it doesn't recognise
your version control system, you can give lists of paths or glob patterns as
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
- Cannot use recursive glob patterns (``**/``)
- Can refer to directories, in which case they include everything under the
  directory, including subdirectories
- Should match the case of the files they refer to, as case-insensitive matching
  is platform dependent

Exclusions have priority over inclusions.
