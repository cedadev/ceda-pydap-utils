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

from paste.httpexceptions import HTTPNotFound
from paste.request import parse_formvars

from ceda.pydap.templatetags import page_utils
from ceda.pydap.utils.multi_download import list_download_files, download_files

logger = logging.getLogger(__name__)

HIDDEN_TAG = re.compile('^(HIDE|HIDDEN).*$')
LOGIN_URL = 'https://auth.ceda.ac.uk/account/signin/'
CEDA_HOME_URL = 'http://www.ceda.ac.uk/'

SAML_TRUSTED_CA_DIR = ''
ATTRIBUTE_SERVICE_URI = ''

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
        
        self.login_url = config.get('login_url', LOGIN_URL)
        self.home_url = config.get('home_url', CEDA_HOME_URL)
        
        self.saml_trusted_ca_dir = config.get('saml_trusted_ca_dir', SAML_TRUSTED_CA_DIR)
        self.attribute_service_uri = config.get('attribute_service_uri', ATTRIBUTE_SERVICE_URI)
    
    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        
        environ['file_root'] = self.root
        
        environ['login_url'] = self.login_url
        environ['home_url'] = self.home_url
        
        environ['saml_trusted_ca_dir'] = self.saml_trusted_ca_dir
        environ['attribute_service_uri'] = self.attribute_service_uri
        
        environ.setdefault('pydap.renderer', self.renderer)
        
        is_directory = False
        
        # check whether the path ends with a slash
        if path_info.endswith(os.path.sep):
            filepath = os.path.abspath(os.path.normpath(os.path.join(
                    self.root,
                    path_info.lstrip('/').replace('/', os.path.sep))))
            assert filepath.startswith(self.root)  # check for ".." exploit
            
            # check for regular file or dir request
            if os.path.exists(filepath):
                # it is actually a file
                if os.path.isfile(filepath):
                    return HTTPNotFound()(environ, start_response)
                # it is a directory
                else:
                    is_directory = True
        
        if is_directory:
            form = parse_formvars(environ)
            if len(form) > 0:
                glob = form.get('glob', '')
                depth = int(form.get('depth', '1'))
                
                action = form.get('action', '')
                if action.lower() == 'download':
                    return download_files(environ, start_response, filepath, glob, depth)
                else:
                    return list_download_files(environ, start_response, filepath, glob, depth)
        
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
