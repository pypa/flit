The pyproject.toml config file
==============================

This file lives next to the module or package.

.. note::

   Older version of Flit (up to 0.11) used a :doc:`flit.ini file <flit_ini>` for
   similar information. Flit can still read these files for now, but you should
   switch to ``pyproject.toml`` soon.

   Run ``python3 -m flit.tomlify`` to convert a ``flit.ini`` file to
   ``pyproject.toml``.

Build system section
--------------------

This tells tools like pip to build your project with flit. It's a standard
defined by PEP 517. For any project using Flit, it will look like this:

.. code-block:: toml

    [build-system]
    requires = ["flit"]
    build-backend = "flit.buildapi"

Metadata section
----------------

This section is called ``[tool.flit.metadata]`` in the file.
There are four required fields:

module
  The name of the module/package, as you'd use in an import statement.
author
  Your name
author-email
  Your email address
home-page
  A URL for the project, such as its Github repository.

e.g. for flit itself

.. code-block:: toml

    [tool.flit.metadata]
    module = "flit"
    author = "Thomas Kluyver"
    author-email = "thomas@kluyver.me.uk"
    home-page = "https://github.com/takluyver/flit"

The remaining fields are optional:

requires
  A list of other packages from PyPI that this package needs. Each package
  may be followed by a version specifier in
  parentheses, like ``(>=4.1)``, and/or an `environment marker
  <https://www.python.org/dev/peps/pep-0345/#environment-markers>`_
  after a semicolon. For example:

  .. code-block:: toml

      requires = ["requests (>=2.6)",
            "configparser; python_version == '2.7'"
      ]

dev-requires
  Packages that are required for development. This field is in the same format
  as ``requires``.

  These are not (yet) encoded in the wheel, but are used when doing
  ``flit install``.
description-file
  A path (relative to the .ini file) to a file containing a longer description
  of your package to show on PyPI. This should be written in `reStructuredText
  <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_, if your long
  description is not valid reStructuredText, a warning will be printed,
  and it will be interpreted as plain text on PyPI.
classifiers
  A list of `Trove classifiers <https://pypi.python.org/pypi?%3Aaction=list_classifiers>`_.
requires-python
  A version specifier for the versions of Python this requires, e.g. ``~=3.3`` or
  ``>=3.3,<4`` which are equivalents.
dist-name
  If you want your package's name on PyPI to be different from the importable
  module name, set this to the PyPI name.
keywords
  Space separated list of words to help with searching for your package.
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
    requires=["requests",
        "docutils",
        "requests_download",
        "pytoml",
    ]
    requires-python="3"
    description-file="README.rst"
    classifiers=["Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]

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
