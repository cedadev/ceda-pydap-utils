'''
Created on 5 Jan 2017

@author: wat
'''

import re

def commify(input):
    """
    Adds commas to numbers. Copied from www.perl.com->FAQ->Files and Formats
    """
    
    result = ""
    
    #TODO: 1 while s/^(-?\d+)(\d{3})/$1,$2/
    
    return result

def localUser():
    """
    Indicates if the client is a 'local' machine.
    """
    host = "" #TODO: $ENV{REMOTE_HOST} || $ENV{REMOTE_ADDR};
    
    if re.match('/.rl.ac.uk$/', host):
        return 1
    else:
        return 0

def validate_filespec(file, valid_root):
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
    
    @param valid_root: Valid top level directory for file, eg "/badc"
    """
    
    if re.match('/^$REQUEST_ROOT/', file):
        
        # my $user  = valid_user();
        user = None #TODO: NDG::Security::Weblogon::username();
        
        # Make sure username is untainted
        user_match = re.match('/(.*)/', user)
        user = user_match.group(0)
        
        if not user:
            return None #TODO: undef, "Not logged in";
        
        file_match = re.match('/^($REQUEST_ROOT\/$user[\/\w\.\-\+]*)$/', file)
        if file_match:
            file = file_match.group(0)
        else:
            return None #TODO: undef, "You are not authorised to view $file";
    
    elif re.match('/^({0}[\/\w\.\-\+\@]*)$/'.format(valid_root), file):
        match = re.match('/^({0}[\/\w\.\-\+\@]*)$/'.format(valid_root), file)
        file = match.group(0)
    
    #Allow access to '/badctest' directory only for local users. This is for testing purposes
    elif re.match('/^(\/badctest[\/\w\.\-\+\@]*)$/', file) and localUser():
        match = re.match('/^(\/badctest[\/\w\.\-\+\@]*)$/', file)
        file = match.group(0)
    
    else:
        return None #TODO: undef
    
    # Check for "../", which could be used to change directory
    if re.match('/\.\.\//', file):
        return None #TODO: undef
    
    # Check that file exists
    if not file:
        return None #TODO: undef
    
    # Remove any trailing slash. ASH 12/11/03
    if re.match('/\/$/', file):
        file = file.strip('/')
    
    return file
