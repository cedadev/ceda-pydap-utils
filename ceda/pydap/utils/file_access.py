'''
Created on 11 Jan 2017

@author: wat
'''

import os

from ceda.pydap.utils.saml import get_user_roles

FTP_ACCESS_FILE = '.ftpaccess'


class FileAccess:
    
    def __init__(self, file_root, directory):
        self.file_root = file_root
        
        assert os.path.isdir(directory)
        self.directory = directory
        
        self._get_limits()
    
    def check_authorisation(self, environ, directory):
        
        #TODO:
        openid = environ.get('REMOTE_USER')
        roles = get_user_roles(environ, openid)
        
        return True
    
    def _get_limits(self):
        self.limits = {}
        
        current_directory = self.directory
        depth = current_directory.count(os.path.sep) - self.file_root.count(os.path.sep) + 1
        while depth > 0:
            self._set_read_limit(current_directory, depth)
            
            current_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
            depth -= 1
    
    def _set_read_limit(self, directory, depth):
        
        ftp_access_path = directory + os.path.sep + FTP_ACCESS_FILE
        
        if os.path.exists(ftp_access_path):
            with open(ftp_access_path) as access_file:
                access_file.readline()
                self.limits[depth] = access_file.readline().strip()
        else:
            self.limits[depth] = 'NONE'
