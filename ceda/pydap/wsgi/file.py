"""
A simple file-based Opendap server.

This class contains file serving features that are
specific to the CEDA implementation of PyDAP.

"""

__author__ = "William Tucker"
__copyright__ = "Copyright (c) 2014, Science & Technology Facilities Council (STFC)"
__license__ = "BSD - see LICENSE file in top-level directory"

import os
import re
import logging

from jinja2 import FileSystemLoader, Environment

from pydap import model
from pydap.wsgi.file import FileServer
from pydap.util.template import FileLoader, Jinja2Renderer

from ceda.pydap.templatetags import page_utils

logger = logging.getLogger(__name__)

HIDDEN_TAG = re.compile('^(HIDE|HIDDEN).*$')
DEFAULT_LOGIN_URL = 'https://auth.ceda.ac.uk/account/signin/'

class CEDAFileServer(FileServer):
    
    def __init__(self, *args, **config):
        super(CEDAFileServer, self).__init__(*args, **config)
        
        loader = FileLoader(config.get('templates', 'templates'))
        template_loader = FileSystemLoader( searchpath=['/', loader.base_directory] )
        template_env = Environment( loader=template_loader )
        
        template_env.globals.update(page_utils.__dict__)
        template_env.globals.update(model.__dict__)
        
        self.renderer = Jinja2Renderer(
                options={}, loader=loader, template_env=template_env)
        
        self.login_url = config.get('login_url', DEFAULT_LOGIN_URL)
    
    def __call__(self, environ, start_response):
        environ['login_url'] = self.login_url
        environ.setdefault('pydap.renderer', self.renderer) 
        
        return super(CEDAFileServer, self).__call__(environ, start_response)
    
    def _is_hidden(self, filepath, **kwargs):
        hidden = super(CEDAFileServer, self)._is_hidden(filepath, **kwargs)
        
        if not hidden and not os.path.isfile(filepath):
            readme_title = page_utils.get_readme_title(filepath)
            
            if HIDDEN_TAG.match(readme_title):
                hidden = True
        
        return hidden

def make_app(global_conf, root, templates, **kwargs):
    return CEDAFileServer(root, templates=templates, **kwargs)
