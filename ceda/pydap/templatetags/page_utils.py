"""
A set of functions for use in a Jinja2 template.

"""

__author__ = "William Tucker"
__copyright__ = "Copyright (c) 2014, Science & Technology Facilities Council (STFC)"
__license__ = "BSD - see LICENSE file in top-level directory"

import os
import re
import logging
import nappy

from __builtin__ import len
from __builtin__ import isinstance
from __builtin__ import enumerate

from urllib2 import quote
from urllib2 import unquote

from urlparse import urlparse

from ceda.pydap.utils.codecs import decode_multi
from ceda.pydap.utils.saml import userid_query

logger = logging.getLogger(__name__)

README_NAME = '00README'

NA_MATCH_REGEX = '.*\.(na)$'

def get_readme_title(directory):
    readme_path = os.path.join(directory, README_NAME)
    
    contents = ''
    try:
        with open(readme_path, 'r') as readme:
            contents = readme.readline().strip()
    except IOError:
        pass
    
    readme_title = decode_multi(contents)
    if not readme_title:
        readme_title = ''
    
    return readme_title

def calculate_dimensions(child):
    dimensions = child.dimensions or ['dim_%id' % j for j in range(len(child.shape))]
    return dimensions

def build_breadcrumbs(environ, mount_path, pathlist):
    # Initialise breadcrumbs with "home" url and label
    breadcrumbs = [
        (environ.get('home_url', ''), 'CEDA'),
        (mount_path, 'Data Server'),
    ]
    
    count = 0
    for _ in pathlist:
        # construct urls & labels for elements in list
        url = mount_path + '/'.join( pathlist[ 0:count+1 ] )
        if not url.endswith('/'):
            url += '/'
        label = pathlist[count]
        breadcrumbs.append( (url, label) )
        count += 1
    
    return breadcrumbs

def parse_cookie(environ, key):
    cookie = environ.get('paste.cookies')[0].get(key)
    cookie_value = None
    if cookie:
        cookie_value = cookie.value
    return cookie_value

def userid(environ, openid):
    return userid_query(environ, openid)

def is_na_file(environ, file_name):
    na_pattern = re.compile(NA_MATCH_REGEX)
    
    if na_pattern.match(file_name):
        return True
    
    path_info = environ.get('PATH_INFO', '').lstrip('/').replace('/', os.path.sep)
    root = environ.get('file_root')
    
    file_path = os.path.abspath(os.path.normpath(os.path.join(
        root,
        path_info,
        file_name
    )))
    assert file_path.startswith(root) # check for ".." exploit
    
    try:
        na_file = nappy.openNAFile(file_path)
        if na_file:
            return True
    except (TypeError, ValueError):
        return False
