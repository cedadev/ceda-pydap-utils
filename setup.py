#!/usr/bin/env python
"""
Added functionality for a CEDA-themed PyDAP distribution

"""
__author__ = "William Tucker"
__copyright__ = "Copyright (c) 2014, Science & Technology Facilities Council (STFC)"
__license__ = "BSD - see LICENSE file in top-level directory"

import os

# Bootstrap setuptools if necessary.
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

THIS_DIR = os.path.dirname(__file__)

SHORT_DESCR = 'CEDA-specific functionality for a PyDAP (https://github.com/pydap/pydap) server.'
try:
    LONG_DESCR = open(os.path.join(THIS_DIR, 'README.md')).read()
except IOError:
    LONG_DESCR = SHORT_DESCR

setup(
    name = 'ceda-pydap-utils',
    version = '0.3.6',
    description = SHORT_DESCR,
    long_description = LONG_DESCR,
    author = 'William Tucker',
    author_email = 'william.tucker@stfc.ac.uk',
    maintainer = 'William Tucker',
    maintainer_email = 'william.tucker@stfc.ac.uk',
    url = 'http://github.com/cedadev/ceda-pydap-utils',
    license = 'BSD - See LICENCE file for details',
    install_requires = [
        'pydap',
        'jinja2',
        'requests',
        'nappy',
        'matplotlib',
        'enum34',
        'webob',
        'pyopenssl',
        'requests',
        'ndg-httpsclient',
        'ndg-saml',
        'ndg-xacml',
    ],
    dependency_links = ["http://dist.ceda.ac.uk/pip/"],
    packages = find_packages(),
    namespace_packages = [
        'ceda',
        'ceda.pydap',
    ],
    include_package_data=True,
    test_suite = 'ceda.pydap.test',
    zip_safe = False
)
