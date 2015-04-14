The flit.ini config file
========================

This file lives next to the module or package. It looks like the following:


   .. code-block:: ini

       [metadata]
       module=foobar
       author=Sir Robin
       author-email=robin@camelot.uk
       home-page=http://github.com/sirrobin/foobar

       # If you want command line scripts, this is how to declare them.
       # If not, you can leave this section out completely.
       [scripts]
       # foobar:main means the script will do: from foobar import main; main()
       foobar=foobar:main



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
  parentheses, like ``(>=4.1)``.
description-file
  A path (relative to the .ini file) to a file containing a longer description
  of your package to show on PyPI. This should be written in `reStructuredText
  <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_.
classifiers
  A list of `Trove classifiers <https://pypi.python.org/pypi?%3Aaction=list_classifiers>`_,
  one per line, indented.
requires-python
  A version specifier for the versions of Python this requires, e.g. ``3`` or
  ``>=3.3``.
dist-name
  If you want your package's name on PyPI to be different from the importable
  module name, set this to the PyPI name.
keywords
  Space separated list of words to help with searching for your package.
license
  The name of a license, if you're using one for which they're isn't a Trove
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
    requires-python=3
    description-file=README.rst
    classifiers=Intended Audience :: Developers
        License :: OSI Approved :: BSD License
        Programming Language :: Python :: 3
        Topic :: Software Development :: Libraries :: Python Modules

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
