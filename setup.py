# -*- coding: utf-8 -*-

from os import path
from setuptools import setup, find_packages


def read(filename):
    with open(path.join(path.dirname(__file__), filename)) as f:
        return f.read()


install_requires = [
    'zope.interface',
    ]

tests_require = [
    'WebOb',
    ]

setup(name='dawnlight',
      version='0.13b2',
      description="A web object publisher",
      long_description="%s\n\n%s" % (
          read('README.txt'), read(path.join('docs', 'HISTORY.txt'))),
      keywords="web publish traverse traversing route routing url",
      author="Martijn Faassen & Dolmen team",
      author_email="faassen@startifact.com, dolmen@list.dolmen-project.org",
      license="BSD",
      packages=find_packages('src', exclude=['ez_setup']),
      package_dir={'': 'src'},
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      extras_require={'test': tests_require},
      entry_points="",
      )
