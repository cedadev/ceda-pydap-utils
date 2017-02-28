'''
Created on 30 Jan 2017

@author: wat
'''

import os

from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime

from paste.request import construct_url
from paste.httpexceptions import HTTPSeeOther

import logging
log = logging.getLogger(__name__)

class DirectoryFilter(object):
    
    def __init__(self, app, prefix=None, **config):
        self._app = app
        self.config = self._parse_config(prefix, config)
        
        self.file_root = config.get('root')
    
    @classmethod
    def filter_app_factory(cls, app, global_conf, prefix=None, **config):
        directory_filter = cls(app, prefix, **config)
        
        return directory_filter
    
    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        
        is_directory = False
        has_trailing_slash = False
        
        # check whether the path ends with a slash
        if path_info.endswith(os.path.sep):
            has_trailing_slash = True
        else:
            filepath = os.path.abspath(os.path.normpath(os.path.join(
                    self.file_root,
                    path_info.lstrip('/').replace('/', os.path.sep))))
            assert filepath.startswith(self.file_root) # check for ".." exploit
            
            # check for regular file or dir request
            if os.path.exists(filepath):
                # it is a directory
                if os.path.isdir(filepath):
                    is_directory = True
        
        if is_directory and not has_trailing_slash:
            return self._redirect(environ, start_response)
        else:
            return self._app(environ, start_response)
    
    def _parse_config(self, prefix, config):
        if prefix:
            prefix += '.'
            
            for key in config:
                new_key = None
                
                if key.startswith(prefix):
                    new_key = key[len(prefix):]
                
                if new_key:
                    config[new_key] = config.pop(key)
        
        return config
    
    def _redirect(self, environ, start_response):
        url = construct_url(environ) + '/'
        
        return HTTPSeeOther(url)(environ, start_response)


class LogoutFilter(object):
    """
    A simple middleware for clearing cookies on logout
    """
    
    def __init__(self, app, prefix=None, **config):
        self._app = app
        
        if prefix:
            prefix = prefix + '.'
        else:
            prefix = ''
        
        self.path = '/'
        self.domain = config.get(prefix + 'domain', '')
        self.logout_path = config.get(prefix + 'logout_path', '/logout')
        
        # Cookies to clear on logout
        cookie_string = config.get(prefix + 'cookies')
        if cookie_string:
            cookie_string = "".join(cookie_string.split())
            self.cookies = cookie_string.split(',')
        else:
            self.cookies = []
    
    @classmethod
    def filter_app_factory(cls, app, global_conf, prefix=None, **config):
        directory_filter = cls(app, prefix, **config)
        
        return directory_filter
    
    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        
        if path_info == self.logout_path:
            log.debug("LogoutFilter.__call__: caught sign out "
                      "path [{0}]".format(self.logout_path))
            
            start_response = self._clear_cookies(start_response)
        
        return self._app(environ, start_response)
    
    def _clear_cookies(self, start_response):
        
        def _start_response(status, header, exc_info=None):
            """Alter the header to tell session cookies to expire"""
            
            stamp = mktime(datetime.min.timetuple())
            expires = format_date_time(stamp)
            cookies = []
            
            for cookie in self.cookies:
                cookies.append(
                    ('Set-Cookie', '{0}=""; Path={1}; Domain={2}; Expires={3}'.format(
                    cookie, self.path, self.domain, expires))
                )
            header.extend(cookies)
            
            return start_response(status, header, exc_info)
        
        return _start_response
