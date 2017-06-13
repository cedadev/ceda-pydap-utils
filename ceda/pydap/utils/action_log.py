'''
Created on 13 Jun 2017

@author: wat
'''

import os
import webob

def format_access_message(environ, extension = '', handler = None, is_directory = False):
    """
    Formats a log message describing a data access request.
    """
    
    request = webob.Request(environ)
    path_info = request.path_info
    
    if is_directory:
        message = '{} accessed directory: {}'.format(
            _user_info(request),
            path_info
        )
        
    else:
        if not extension:
            extension = 'default'
        
        if request.path_info.endswith(extension):
            path_info, _ = os.path.splitext(path_info)
        
        description = 'no handler'
        if handler:
            description = 'no response'
            
            extension_name = extension.replace('.', '')
            response = handler.response_map.get(extension_name)
            if response:
                description = '"{}" response'.format(extension_name)
        
        message = '{} accessed file: {} - extension: {} ({})'.format(
            _user_info(request),
            path_info,
            extension,
            description
        )
    
    return message

def format_action_message(environ, action, description = 'no description'):
    """
    Formats a log message describing an action related to a request.
    """
    
    request = webob.Request(environ)
    
    message = '{} performed action [{}] at: {} - {}'.format(
        _user_info(request),
        action,
        request.path_info,
        description
    )
    
    return message

def _user_info(request):
    
    if request.remote_user:
        return '{} - [{}]'.format(request.remote_addr, request.remote_user)
    else:
        return '{} - anonymous user'.format(request.remote_addr)
