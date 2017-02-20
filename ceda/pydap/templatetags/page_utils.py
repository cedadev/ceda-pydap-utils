"""
A set of functions for use in a Jinja2 template.

"""

__author__ = "William Tucker"
__copyright__ = "Copyright (c) 2014, Science & Technology Facilities Council (STFC)"
__license__ = "BSD - see LICENSE file in top-level directory"

import os
import re
import logging

from __builtin__ import len
from __builtin__ import isinstance
from __builtin__ import enumerate

from urllib2 import quote
from urllib2 import unquote

from urlparse import urlparse

logger = logging.getLogger(__name__)

README_NAME = '00README'

NA_MATCH_REGEX = '.*\.(em1|em2|em3|nox|cn7|fm1|jn1|jo1|jo4|o30|pr1|pn2|hc5)$'

def get_readme_title(directory):
    readme_title = ''
    readme_path = os.path.join(directory, README_NAME)
    try:
        with open(readme_path, 'r') as readme:
            first_line = readme.readline()
            readme_title = first_line.strip()
    except IOError:
        pass
    
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

def is_na_file(file_name):
    na_pattern = re.compile(NA_MATCH_REGEX)
    
    if na_pattern.match(file_name):
        return True
