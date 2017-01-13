'''
Created on 11 Jan 2017

@author: wat
'''

import os
import re

from enum import Enum

from ceda.pydap.utils.saml import get_user_roles

FTP_ACCESS_FILE = '.ftpaccess'

READ_LIMIT_RE = '<limitread>'
LIMIT_END_RE = '</limit>'


class AccessRules(Enum):
    ALLOW_ALL = 'allowall'
    DENY_ALL = 'denyall'
    ALLOW_GROUP = 'allowgroup'


class AccessLimit:
    ALLOW_DEFAULT = True
    
    def __init__(self, rules):
        self.allow = self.ALLOW_DEFAULT
        self.roles_required = []
        
        self._determine_limit(rules)
    
    def get_roles_required(self):
        return self.roles_required
    
    def allowed(self):
        if len(self.roles_required) > 0:
            return True
        else:
            return self.allow
    
    def _determine_limit(self, rules):
        for rule in rules:
            rule = rule.split()
            
            name = rule[0]
            properties = rule[1:]
            
            if name == AccessRules.ALLOW_ALL.value:
                self.allow = True
            elif name == AccessRules.DENY_ALL.value:
                self.allow = False
            elif name == AccessRules.ALLOW_GROUP.value:
                self.roles_required = properties


class FileAccess:
    
    def __init__(self, file_root):
        self.file_root = file_root
        self.rel_root = self._make_relative(file_root)
        
        self.limits = {}
        self._get_limit(self.rel_root)
    
    def check_authorisation(self, environ, directory_path):
        rel_path = self._make_relative(directory_path)
        
        limit_tree = self._get_limit(rel_path)
        
        #TODO:
        openid = environ.get('REMOTE_USER')
        roles = get_user_roles(environ, openid)
        if not roles:
            roles = []
        
        return self._has_access(limit_tree, roles)
    
    def _has_access(self, limit_tree, roles):
        has_access = False
        
        #TODO:
        for limit in limit_tree:
            if limit.allowed():
                missing_role = False
                for required_role in limit.get_roles_required():
                    if not required_role in roles:
                        missing_role = True
                        break
                
                if not missing_role:
                    has_access = True
        
        return has_access
    
    def _make_relative(self, full_path):
        assert os.path.isdir(full_path)
        abs_path = os.path.abspath(full_path)
        prefix = os.path.commonprefix([abs_path, self.file_root])
        
        if prefix == self.file_root:
            rel_path = os.path.relpath(abs_path, self.file_root)
            return rel_path
        else:
            return None
    
    def _get_limit(self, directory):
        limit_tree = []
        
        cached_limit = self.limits.get(directory)
        if cached_limit:
            limit_tree.append(cached_limit)
            return limit_tree
        
        current_directory = directory
        depth = directory.count(os.path.sep) + 1
        while depth > 0:
            rules = self._parse_access_file(current_directory)
            
            access_limit = AccessLimit(rules)
            limit_tree.append(access_limit)
            self.limits[current_directory] = access_limit
            
            current_directory = os.path.dirname(current_directory)
            depth -= 1
        
        if not directory == self.rel_root:
            limit_tree.append(self.limits.get(self.rel_root))
        
        return limit_tree
    
    def _parse_access_file(self, directory):
        ftp_access_path = os.path.join(
            self.file_root, directory, FTP_ACCESS_FILE
        )
        
        rules = []
        if os.path.exists(ftp_access_path):
            with open(ftp_access_path) as access_file:
                
                read_limit_open = False
                for line in access_file:
                    line_clean = ''.join(line.split()).lower()
                    if re.match(READ_LIMIT_RE, line_clean):
                        read_limit_open = True
                        
                    elif read_limit_open:
                        if not re.match(LIMIT_END_RE, line_clean):
                            line = ' '.join(line.split()).lower()
                            rules.append(line)
                        else:
                            break
        
        return rules
