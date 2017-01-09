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

from zipfile import ZipFile
import shutil

from jinja2 import FileSystemLoader, Environment

from pydap import model
from pydap.wsgi.file import FileServer
from pydap.util.template import FileLoader, Jinja2Renderer

from paste.httpexceptions import HTTPNotFound
from paste.fileapp import FileApp

from ceda.pydap.templatetags import page_utils
from ceda.pydap.utils.multi_download import download_files

logger = logging.getLogger(__name__)

HIDDEN_TAG = re.compile('^(HIDE|HIDDEN).*$')
LOGIN_URL = 'https://auth.ceda.ac.uk/account/signin/'
CEDA_HOME_URL = 'http://www.ceda.ac.uk/'

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
    
    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        
        environ['login_url'] = self.login_url
        environ['home_url'] = self.home_url
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
            pass
        
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
