Publishing to TestPyPI
======================

To publish a package to TestPyPI:

1. Edit your ``~/.pypirc`` file as follows::

       [distutils]
       index-servers =
           pypi
           testpypi

       [testpypi]
       repository = https://test.pypi.org/legacy/
       username:<your_testPyPI_username>
       password:<your_testPyPI_password>

       [pypi]
       username:<your_PyPI_username>
       password:<your_PyPI_password>

2. Run this command to upload your code to TestPyPI::

       flit --repository testpypi publish
