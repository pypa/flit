Why use Flit?
=============

*Make the easy things easy and the hard things possible* is an old motto from
the Perl community. Flit is entirely focused on the *easy things* part of that,
and leaves the hard things up to other tools.

Specifically, the easy things are pure Python packages with no build steps
(neither compiling C code, nor bundling Javascript, etc.). The vast majority of
packages on PyPI are like this: plain Python code, with maybe some static data
files like icons included.

It's easy to underestimate the challenges involved in distributing and
installing code, because it seems like you just need to copy some files into
the right place. There's a whole lot of metadata and tooling that has to work
together around that fundamental step. But with the right tooling, a developer
who wants to release their code doesn't need to know about most of that.

What, specifically, does Flit make easy?

- ``flit init`` helps you set up the information Flit needs about your
  package.
- Subpackages are automatically included: you only need to specify the
  top-level package.
- Data files within a package directory are automatically included.
  Missing data files has been a common packaging mistake with other tools.
- The version number is taken from your package's ``__version__`` attribute,
  so that always matches the version that tools like pip see.
- ``flit publish`` uploads a package to PyPI, so you don't need a separate tool
  to do this.

Setuptools, the most common tool for Python packaging, now has shortcuts for
many of the same things. But it has to stay compatible with projects published
many years ago, which limits what it can do by default.

Flit also has some support for :doc:`reproducible builds <reproducible>`,
a feature which some people care about.

There have been many other efforts to improve the user experience of Python
packaging, such as `pbr <https://pypi.org/project/pbr/>`_, but before Flit,
these tended to build on setuptools and distutils. That was a pragmatic
decision, but it's hard to build something radically different on top of those
libraries. The existence of Flit spurred the development of new standards,
like :pep:`518` and :pep:`517`, which are now used by other packaging tools
such as `Poetry <https://python-poetry.org/>`_ and
`Enscons <https://pypi.org/project/enscons/>`_.

Other options
-------------

If your package needs a build step, you won't be able to use Flit.
`Setuptools <https://setuptools.readthedocs.io/en/latest/>`_ is the de-facto
standard, but newer tools such as Enscons_ also cover this case.

Flit also doesn't help you manage dependencies: you have to add them to
``pyproject.toml`` by hand. Tools like Poetry_ and `Pipenv
<https://pypi.org/project/pipenv/>`_ have features which help add and update
dependencies on other packages.
