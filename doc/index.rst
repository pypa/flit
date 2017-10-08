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
   upload
   reproducible
   history

Environment variables
---------------------

.. envvar:: FLIT_NO_NETWORK

   .. versionadded:: 0.10

   Setting this to any non-empty value will stop flit from making network
   connections (unless you explicitly ask to upload a package). This
   is intended for downstream packagers, so if you use this, it's up to you to
   ensure any necessary dependencies are installed.

.. envvar:: FLIT_ROOT_INSTALL

   By default, ``flit install`` will fail when run as root on POSIX systems,
   because installing Python modules systemwide is not recommended. Setting
   this to any non-empty value allows installation as root. It has no effect on
   Windows.

There are other environment variables to control :doc:`uploading packages <upload>`.
and :doc:`reproducible builds <reproducible>`.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

