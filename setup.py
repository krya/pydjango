#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='pydjango',
    version='0.0.1',
    description='pytest plugin for django Framework',
    author='Denis K.',
    author_email='sinedone@gmail.com',
    url='https://github.com/krya/pydjango',
    packages=['pydjango'],
    long_description=read('README.rst'),
    install_requires=['pytest>=2.3.4'],
    classifiers=['Framework :: Django',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: MIT License',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python',
                 'Topic :: Software Development :: Testing'],
    # the following makes a plugin available to py.test
    entry_points={'pytest11': ['pydjango = pydjango.plugin']})
