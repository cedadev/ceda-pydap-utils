'''
Created on 21 Feb 2017

@author: wat
'''

import os


def validate_path(application_root, path):
    """
    Checks that the given file specification is valid.  
    
    Performs security checks on the given file specification to make sure that
    it does not try and use invalid characters or access a directory that it is
    not allowed to.
    
    If successful then an 'untainted' copy of the given filespecification is
    returned. This must be used to prevent failure when the program is run as
    a setuid script. If the checks failed then undef is returned.
    
    Have now added a separate check for file in the 'requests' directory. User
    is only allowed to see their own sub-directory.
    
    @param application_root: top level directory for serving files
    """
    
    # Check for "../", which could be used to change directory
    path = os.path.abspath(path)
    
    # Remove any trailing slash
    path = path.rstrip(os.path.sep)
    
    # Check that path exists
    if not os.path.exists(path):
        raise ValueError('Path does not exist')
    
    # Check that the path and application have a common root
    prefix = os.path.commonprefix([path, application_root])
    
    if not prefix == application_root:
        raise ValueError('Path root does not match application root')
    
    return path
