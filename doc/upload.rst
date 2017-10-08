Controlling package uploads
===========================

The command ``flit publish`` will upload your package to a package index server.
The default settings let you upload to `PyPI <https://pypi.org/>`_,
the default Python Package Index, with a single user account.

If you want to upload to other servers, or with more than one user account,
or upload packages from a continuous integration job,
you can configure Flit in two main ways:

Using .pypirc
-------------

You can create or edit a config file in your home directory, ``~/.pypirc``.
This is also used by other Python tools such as `twine
<https://pypi.python.org/pypi/twine>`_.

For instance, to upload a package to the `Test PyPI server <https://test.pypi.org/>`_
instead of the normal PyPI, use a config file looking like this:

.. code-block:: ini

    [distutils]
    index-servers =
       pypi
       testpypi

    [pypi]
    repository = https://upload.pypi.org/legacy/
    username = sirrobin  # Replace with your PyPI username

    [testpypi]
    repository = https://test.pypi.org/legacy/
    username = sirrobin  # Replace with your TestPyPI username

You can select an index server from this config file with the
``--repository`` option::

    flit --repository testpypi publish

If you don't use this option,
Flit will use the server called ``pypi`` in the config file. If that doesn't
exist, it uses

If you publish a package and you don't have a ``.pypirc`` file, Flit will create
it to store your username.

Flit tries to store your password securely using the
`keyring <https://pypi.python.org/pypi/keyring>`_ library.
If keyring is not installed, Flit will ask for your password for each upload.
Alternatively, you can also manually add your password to the ``.pypirc`` file
(``password = ...``)

Using environment variables
---------------------------

.. envvar:: FLIT_USERNAME
            FLIT_PASSWORD
            FLIT_INDEX_URL

   .. versionadded:: 0.11

   Set a username, password, and index URL for uploading packages.

Environment variables take precedence over the config file, except if you use
the ``--repository`` option to explicitly pick a server from the config file.
