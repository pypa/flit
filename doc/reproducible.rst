Reproducible builds
===================

.. versionadded:: next

Wheels built by flit are reproducible: if you build from the same source code,
you should be able to make wheels that are exactly identical, byte for byte.
This is useful for verifying software. For more details, see
`reproducible-builds.org <https://reproducible-builds.org/>`__.

There are a couple of caveats, however:

First, zip files include the modification timestamp from each file. This will
probably be different on each computer, because it indicates when your local
copy of the file was written, not when it was changed in version control. To
make reproducible builds, set the
`SOURCE_DATE_EPOCH <https://reproducible-builds.org/specs/source-date-epoch/>`__
environment variable before building, and document what value you used. This
overrides the timestamps. On Unix systems, you can get a value for the current
time by running::

    date +%s

