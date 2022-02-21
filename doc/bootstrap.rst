Bootstrapping
=============

Flit is itself packaged using Flit, as are some foundational packaging tools
such as ``pep517``. So where can you start if you need to install everything
from source?

.. note::

   For most users, ``pip`` handles all this automatically. You should only need
   to deal with this if you're building things entirely from scratch, such as
   putting Python packages into another package format.

The key piece is ``flit_core``. This is a package which can build itself using
nothing except Python and the standard library. From an unpacked source archive,
you can make a wheel by running::

    python -m flit_core.wheel

And then you can install this wheel with the ``bootstrap_install.py`` script
included in the sdist (or by unzipping it to the correct directory)::

    # Install to site-packages for this Python:
    python bootstrap_install.py dist/flit_core-*.whl

    # Install somewhere else:
    python bootstrap_install.py --installdir /path/to/site-packages dist/flit_core-*.whl

As of version 3.6, flit_core bundles the ``tomli`` TOML parser, to avoid a
dependency cycle. If you need to unbundle it, you will need to special-case
installing flit_core and/or tomli to get around that cycle.

After ``flit_core``, I recommend that you get `installer
<https://pypi.org/project/installer/>`_ set up. You can use
``python -m flit_core.wheel`` again to make a wheel, and then use installer
itself (from the source directory) to install it.

After that, you probably want to get `build <https://pypi.org/project/build/>`_
and its dependencies installed as the goal of the bootstrapping phase. You can
then use ``build`` to create wheels of any other Python packages, and
``installer`` to install them.
