Reproducible builds
===================

.. versionadded:: 0.8

Wheels built by flit are reproducible: if you build from the same source code,
you should be able to make wheels that are exactly identical, byte for byte.
This is useful for verifying software. For more details, see
`reproducible-builds.org <https://reproducible-builds.org/>`__.

There is a caveat, however: wheels (which are zip files) include the
modification timestamp from each file. This will
probably be different on each computer, because it indicates when your local
copy of the file was written, not when it was changed in version control.
These timestamps can be overridden by the environment variable
:envvar:`SOURCE_DATE_EPOCH`.

.. code-block:: shell

   SOURCE_DATE_EPOCH=$(date +%s)
   flit publish
   # Record the value of SOURCE_DATE_EPOCH in release notes for reproduction

.. versionchanged:: 0.12
   Normalising permission bits

Flit normalises the permission bits of files copied into a wheel to either
755 (executable) or 644. This means that a file is readable by all users
and writable only by the user who owns it.

The most popular version control systems only track the executable bit,
so checking out the same repository on systems with different umasks
(e.g. Debian and Fedora) produces files with different permissions. With Flit
0.11 and earlier, this difference would produce non-identical wheels.
