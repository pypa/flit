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
you can run ``python build_dists.py``, of which the crucial part is::

    from flit_core import build_thyself
    whl_fname = build_thyself.build_wheel('dist/')
    print(os.path.join('dist', whl_fname))

This produces a ``.whl`` wheel file, which you can unzip into your
``site-packages`` folder (or equivalent) to make ``flit_core`` available for
building other packages. (You could also just copy ``flit_core`` from the
source directory, but without the ``.dist-info`` folder, tools like pip won't
know that it's installed.)

As of version 3.6, flit_core bundles the ``tomli`` TOML parser, to avoid a
dependency cycle. If you need to unbundle it, you will need to special-case
installing flit_core and/or tomli to get around that cycle.

I recommend that you get the `build <https://pypi.org/project/build/>`_ and
`installer <https://pypi.org/project/installer/>`_ packages (and their
dependencies) installed as the goal of the bootstrapping phase. These tools
together can be used to install any other Python packages: ``build`` to create
wheels and ``installer`` to install them.
