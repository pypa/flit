"""
Module to generate a setup.py file for a flit project.
"""

from . import common

TEMPLATE = \
"""# this file has been auto generated. Do not edit.

import os

def find_packages(name):
    packages = []
    for dir,subdirs,files in os.walk(name):
        package = dir.replace(os.path.sep, '.')
        if '__init__.py' not in files:
            # not a package
            continue
        packages.append(package)
    return packages


from setuptools import setup

setup(name='{name}',
      version='{version}',
      description={description},
      url='{url}',
      author='{author}',
      author_email='{email}',
      license='{license}',
      packages=find_packages({packages}),
      python_requires='{requires_python}',
      install_requires=[
          {install_requires}
      ],
      zip_safe=False)
# this file has been auto generated. Do not edit.
"""


def generate_setup_py(ini_file):
    meta, mod = common.metadata_and_module_from_ini_path(ini_file)
    return TEMPLATE.format(
            name=meta.name,
            version=meta.version,
            description=repr(meta.description),
            url=meta.home_page,
            author=meta.author,
            email=meta.author_email,
            license=meta.license,
            packages=repr(meta.name),
            requires_python=meta.requires_python,
            install_requires=repr(list(meta.requires_dist)+list(meta.requires)),
            )
        

