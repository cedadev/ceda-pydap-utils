'''
Created on 11 Jan 2017

@author: wat
'''

import os
import webob

from ndg.saml.saml2.core import DecisionType

from ceda.pydap.utils.saml import get_authz_decision


class FileAccess:
    APPEND_STRING = 'APPEND'
    
    def __init__(self, environ):
        self.environ = environ
        request = webob.Request(environ)
        self.application_url = request.application_url
        # Nb. user may not be logged in hence REMOTE_USER is not set
        self.remote_user = request.remote_user or ''
        
        self.file_root = environ.get('file_root')
    
    def has_access(self, path):
        decision = self.authorisation_decision(path)
        
        if decision == DecisionType.PERMIT:
            return True
        else:
            return False
    
    def authorisation_decision(self, path):
        assert os.path.exists(path)
        
        rel_path = self._make_relative(path)
        url = self._build_url(rel_path, os.path.isdir(path))
        
        decision = get_authz_decision(
            self.environ,
            url,
            self.remote_user
        )
        
        return decision
    
    def _make_relative(self, full_path):
        abs_path = os.path.abspath(full_path)
        
        prefix = os.path.commonprefix([abs_path, self.file_root])
        
        if prefix == self.file_root:
            rel_path = os.path.relpath(abs_path, self.file_root)
            return rel_path
        else:
            return None
    
    def _build_url(self, rel_path, is_dir):
        if not os.path.sep == '/':
            rel_path = rel_path.replace(os.path.sep, '/')
        
        if is_dir:
            url = ''.join([
                self.application_url, '/',
                rel_path, '/',
                self.APPEND_STRING
            ])
        
        return url
