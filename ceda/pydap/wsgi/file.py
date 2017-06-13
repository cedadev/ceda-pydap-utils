"""
A simple file-based Opendap server.

This class contains file serving features that are
specific to the CEDA implementation of PyDAP.

"""
from ceda.pydap.views.file_plot import FilePlotView

__author__ = "William Tucker"
__copyright__ = "Copyright (c) 2014, Science & Technology Facilities Council (STFC)"
__license__ = "BSD - see LICENSE file in top-level directory"

import os
import re
import logging

from jinja2 import FileSystemLoader, Environment

from pydap import model
from pydap.wsgi.file import FileServer
from pydap.handlers.lib import get_handler
from pydap.util.template import FileLoader, Jinja2Renderer

from paste.httpexceptions import HTTPNotFound
from paste.request import parse_formvars

from ceda.pydap.templatetags import page_utils
from ceda.pydap.views.multi_download import MultiFileView
from ceda.pydap.utils.action_log import format_access_message

logger = logging.getLogger(__name__)

HIDDEN_TAG = re.compile('^(HIDE|HIDDEN).*$')
LOGIN_URL = 'https://auth.ceda.ac.uk/account/signin/'
CEDA_HOME_URL = 'http://www.ceda.ac.uk/'

SAML_TRUSTED_CA_DIR = ''
AUTHZ_SERVICE_URI = ''
ATTR_SERVICE_URI = ''

class CEDAFileServer(FileServer):
    
    def __init__(self, *args, **config):
        super(CEDAFileServer, self).__init__(*args, **config)
        
        logger.info("Starting CEDA PyDAP utils fileserver.")
        
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
        self.authz_service_uri = config.get('authz_service_uri', AUTHZ_SERVICE_URI)
        self.attr_service_uri = config.get('attr_service_uri', ATTR_SERVICE_URI)
    
    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        
        environ['file_root'] = self.root
        
        environ['login_url'] = self.login_url
        environ['home_url'] = self.home_url
        
        environ['saml_trusted_ca_dir'] = self.saml_trusted_ca_dir
        environ['authz_service_uri'] = self.authz_service_uri
        environ['attr_service_uri'] = self.attr_service_uri
        
        environ.setdefault('pydap.renderer', self.renderer)
        
        is_directory = False
        
        filepath = os.path.abspath(os.path.normpath(os.path.join(
                self.root,
                path_info.lstrip('/').replace('/', os.path.sep))))
        basename, extension = os.path.splitext(filepath)
        assert filepath.startswith(self.root)  # check for ".." exploit
        
        # check whether the path ends with a slash
        if path_info.endswith(os.path.sep):
            # check for regular file or dir request
            if os.path.exists(filepath):
                # it is actually a file
                if os.path.isfile(filepath):
                    return HTTPNotFound()(environ, start_response)
                # it is a directory
                else:
                    is_directory = True
        
        # Check if the filepath is a path in the archive
        if self._is_data_path(filepath):
            
            form = parse_formvars(environ)
            
            if is_directory:
                
                if len(form) > 0:
                    glob = form.get('glob', '')
                    depth = int(form.get('depth', '1'))
                    
                    try:
                        multi_file_view = MultiFileView(environ, start_response, filepath, glob, depth)
                        
                        action = form.get('action', '')
                        if action.lower() == 'download':
                            
                            # Download mutiple files.
                            return multi_file_view.download_files()
                        else:
                            
                            # Preview mutiple files for download.
                            return multi_file_view.list_files()
                    
                    except ValueError as e:
                        logger.error((
                            "An exception has occurred parsing "
                            "multiple files for {0}: {1}".format(filepath, e)
                        ))
            else:
                
                if 'plot' in form:
                    file_plot_view = FilePlotView(environ, start_response, filepath, form)
                    
                    if form.get('plot') == 'img':
                        
                        # Generate a plot image from the file.
                        return file_plot_view.generate()
                    else:
                        
                        # Load a form for plotting a file.
                        return file_plot_view.form()
            
            # No specific action taken.
            # Log access.
            logger.info(format_access_message(environ, is_directory = is_directory))
        
        # Check if the filepath without its extension is a path in the archive
        elif self._is_data_path(basename):
            
            # File could be being handled by a handler.
            handler = get_handler(basename, self.handlers)
            
            # Log access.
            logger.info(format_access_message(environ, extension, handler))
        
        return super(CEDAFileServer, self).__call__(environ, start_response)
    
    def _is_hidden(self, filepath, **kwargs):
        hidden = super(CEDAFileServer, self)._is_hidden(filepath, **kwargs)
        
        if not hidden and not os.path.isfile(filepath):
            readme_title = page_utils.get_readme_title(filepath)
            
            if HIDDEN_TAG.match(readme_title):
                hidden = True
        
        return hidden
    
    def _is_data_path(self, filepath):
        
        if not os.path.exists(filepath):
            return False
        
        relative_filepath = os.path.relpath(filepath, self.root)
        
        # Check for favicon
        if relative_filepath == 'favicon.ico':
            return False
        
        # Check if the path points to the static content directory
        if relative_filepath.startswith('.static' + os.path.sep):
            return False
        
        return True

def make_app(global_conf, root, templates, **kwargs):
    return CEDAFileServer(root, templates=templates, **kwargs)
