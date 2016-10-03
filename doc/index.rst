Flit |version|
==============

.. raw:: html

   <img src="_static/flit_logo_nobg_cropped.svg" width="200px" style="float: right"/>

.. include:: ../README.rst

Contents:

.. toctree::
   :maxdepth: 2

   flit_ini
   entrypoints
   history

Environment variables
---------------------

.. envvar:: FLIT_ROOT_INSTALL

   By default, ``flit install`` will fail when run as root on POSIX systems,
   because installing Python modules systemwide is not recommended. Setting
   this to any non-empty value allows installation as root. It has no effect on
   Windows.

.. envvar:: SOURCE_DATE_EPOCH

   To make reproducible builds, set this to a timestamp as a number of seconds
   since the start of the year 1970 in UTC. See `the specification
   <https://reproducible-builds.org/specs/source-date-epoch/>`__ for more
   details.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

