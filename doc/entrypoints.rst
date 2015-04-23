Specifying entry points
=======================

The most common use of entry points is the ``console_scripts`` section for
installing system commands. You can specify these in the :ref:`Scripts section
<flit_ini_scripts>` of ``flit.ini``.

If you need other entry points, e.g. to distribute a plugin for an application,
you should store these in an ``entry_points.txt`` file next to ``flit.ini``.
The format is like this:

.. code-block:: ini

    [group]
    name1=package.module:func
    name2=package:obj

    # e.g.
    [calculator.plugins]
    romannumerals=romancalc:init

In each ``package:name`` value, the part before the colon should be an
importable module name, and the latter part should be the name of an object
accessible within that module. The details of what object to expose depend on
the application you're extending.

If you need to name the entry points file something else, you can tell flit its
name by adding a ``entry-points-file`` key in the ``[metadata]`` section of
``flit.ini``.