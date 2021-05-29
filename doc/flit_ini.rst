:orphan:

The flit.ini config file
========================

This file lives next to the module or package.

.. note::

   Flit 0.12 and above uses a :doc:`pyproject.toml file <pyproject_toml>` file
   to store this information. Run ``python3 -m flit.tomlify`` to convert a
   ``flit.ini`` file to ``pyproject.toml``.

Metadata section
----------------

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

.. code-block:: ini

    [metadata]
    module=flit
    author=Thomas Kluyver
    author-email=thomas@kluyver.me.uk
    home-page=https://github.com/takluyver/flit

The remaining fields are optional:

requires
  A list of other packages from PyPI that this package needs. Each package
  should be on its own line, and may be followed by a version specifier in
  parentheses, like ``(>=4.1)``, and/or an `environment marker
  <https://www.python.org/dev/peps/pep-0345/#environment-markers>`_
  after a semicolon. For example:

  .. code-block:: ini

      requires = requests (>=2.6)
            configparser; python_version == '2.7'

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
  A list of `Trove classifiers <https://pypi.python.org/pypi?%3Aaction=list_classifiers>`_,
  one per line, indented.
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

Here's the full example from flit itself:

.. code-block:: ini

    [metadata]
    author=Thomas Kluyver
    author-email=thomas@kluyver.me.uk
    home-page=https://github.com/takluyver/flit
    requires=requests
    requires-python= >=3
    description-file=README.rst
    classifiers=Intended Audience :: Developers
        License :: OSI Approved :: BSD License
        Programming Language :: Python :: 3
        Topic :: Software Development :: Libraries :: Python Modules

.. _flit_ini_scripts:

Scripts section
---------------

Each key and value in this describes a shell command to be installed along with
your package. These work like setuptools 'entry points'. Here's the section
for flit:

.. code-block:: ini

    [scripts]
    flit = flit:main

This will create a ``flit`` command, which will call the function ``main()``
imported from :mod:`flit`.
