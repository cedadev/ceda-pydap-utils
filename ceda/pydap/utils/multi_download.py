'''
Created on 6 Jan 2017

@author: wat
'''

import os
import re
import glob

import logging
logger = logging.getLogger(__name__)

from zipfile import ZipFile
from paste.fileapp import FileApp
from paste.request import construct_url
from pydap.lib import __version__

from ceda.pydap.utils.file_access import FileAccess

# Max size (in uncompressed bytes) that can be downloaded
MAX_DOWNLOAD_SIZE = 3000000000
# Maximum number of files to display on a page
MAX_DISPLAY_FILES = 10000
# Maximum directory depth allowed
MAX_DEPTH = 3
# Default extension to be used for gzipped tar files
EXT = ".tgz"

DEFAULT_ACTION = "none"


class WebFile:
    """
    @param full_path: Full path of file
    @param allowed: Whether or not the file is readable by the remote user
    """
    
    def __init__(self, full_path, allowed):
        self.full_path = full_path
        
        self.allowed = allowed
        
        try:
            self.size = self._calculate_size()
        except os.error:
            self.size = 0
    
    def _calculate_size(self):
        return os.path.getsize(self.full_path)


class MultiFileHandler:
    '''
    Class providing utilities for identifying multiple files
    within a directory using Unix-style glob pattern matching
    '''
    
    DISALLOWED_FILENAMES = ['index.html']
    
    def __init__(self, environ, directory, glob_string='*', max_depth=1):
        assert os.path.isdir(directory)
        self.directory = directory
        
        self.disallowed_filenames = environ.get(
            'disallowed_filenames',
            self.DISALLOWED_FILENAMES
        )
        
        self.file_access = FileAccess(environ)
        self.identify_files(directory, glob_string, max_depth)
    
    def identify_files(self, directory, glob_string, max_depth):
        """
        Returns a list of WebFile object references for the files which have been 
        selected to download. This list includes files for which the user does not
        have read permission, so this needs to be checked before downloading the
        files.
        
        Note that I have made some changes to this routine to increace the speed when
        the directory contains a large number of files. In particular I perform a
        specific test for each filename, rather than using generalised grep statements
        to weed out the files which are not required.
        
        @param directory: Directory containing files to be selected
        @param glob_string: glob containing specification for files to be downloaded
        @param depth: How many directories to go down
        """
        
        self.files = []
        self.max_depth = max_depth
        
        # Retrieve all files in directory
        current_depth = 1
        self._glob_traverse(directory, glob_string, current_depth)
        
        return self.files
    
    def file_stats(self):
        """
        Returns information about the total number and size of the files selected.
        Returns the number of files for which access is allowed, the number of files
        for which the user does not have read access and the total size of the files
        for which access is allowed
        
        @param files: Array of WebFile references for selected files
        """
        
        n_allowed = 0
        n_forbidden = 0
        allowed_size = 0
        
        for web_file in self.files:
            
            if web_file.allowed:
                n_allowed += 1
                allowed_size += web_file.size
            else:
                n_forbidden += 1
        
        return (n_allowed, n_forbidden, allowed_size)
    
    def _glob_traverse(self, directory, glob_string, current_depth):
        '''
        Recursively descend, depth first, into a directory based on
        glob pattern and maximum depth. Saves new WebFile objects from
        discovered file paths.
        '''
        
        if current_depth <= self.max_depth:
            
            # Grab the left-most glob expression
            parts = glob_string.split(os.path.sep)
            #TODO:
            current_glob = parts[0]
            remaining_glob = os.path.sep.join(parts[1:])
            full_glob = os.path.join(directory, current_glob)
            
            # Check user authorisation for directory
            read_allowed = self.file_access.has_access(directory)
            
            for path in glob.iglob(full_glob):
                
                # Check each path to see if we should process it
                if os.path.isfile(path):
                    
                    # Filter out unwanted files - files beginning with '.'  and index.html files
                    filename = os.path.basename(path)
                    if self._is_valid(filename):
                        web_file = WebFile(path, read_allowed)
                        self.files.append(web_file)
                    
                elif os.path.isdir(path):
                    new_depth = current_depth + 1
                    self._glob_traverse(path, remaining_glob, new_depth)
    
    def _is_valid(self, filename):
        '''
        Checks that a file name does not begin with a dot matches
        a forbidden string.
        '''
        is_valid = True
        
        if filename.startswith('.'):
            is_valid = False
        
        if filename in self.disallowed_filenames:
            is_valid = False
        
        return is_valid


class MultiFileView:
    '''
    Class for serving different multi-file download views
    using a Jinja2 template engine and a MultiFileHandler.
    '''
    
    def __init__(self, environ, directory, glob_string='*', depth=1):
        self.environ = environ
        
        # File specification string
        glob_string = validate_glob(glob_string)
        self.glob_string = glob_string
        
        if depth > MAX_DEPTH:
            depth = MAX_DEPTH
        self.depth = depth
        
        # Validate path
        directory = validate_path(environ.get('file_root'), directory)
        self.directory = directory
        
        self.multi_file_handler = MultiFileHandler(
            environ,
            directory,
            glob_string,
            depth
        )
    
    def list_files(self, start_response):
        """
        Returns a view listing information about files to be downloaded
        """
        
        web_files = self.multi_file_handler.files
        
        n_files = 0
        allowed_files = []
        for web_file in web_files:
            n_files += 1
            if n_files >= MAX_DISPLAY_FILES:
                break
            
            if web_file.allowed:
                file_path = web_file.full_path
                
                relative_path = ".{0}{1}".format(
                    os.path.sep,
                    os.path.relpath(file_path, self.directory)
                )
                
                file_details = {
                    'relative_path': relative_path,
                    'size': web_file.size
                }
                
                allowed_files.append(file_details)
        
        context = self._build_context(allowed_files)
        
        renderer = self.environ.get('pydap.renderer')
        template = renderer.loader('selected_files.html')
        
        content_type = 'text/html'
        output = renderer.render(
            template,
            context,
            output_format=content_type
        )
        
        headers = [('Content-type', content_type)]
        start_response("200 OK", headers)
        
        return [output.encode('utf-8')]
    
    def download_files(self, start_response):
        """
        Downloads the requested set of files as a single gzipped-tar file
        
        @param directory: Reference to path of the active directory
        @param glob: Filename glob specifying files to be downloaded
        """
        
        # Check total size of files and exit with error message if too big
        _, _, allowedSize = self.multi_file_handler.file_stats()
        if allowedSize > MAX_DOWNLOAD_SIZE:
            #TODO:
            return None
        
        web_files = self.multi_file_handler.files
        
        default_tmp_dir = os.path.join(os.path.dirname(__file__), 'tmp')
        tmp_root = self.environ.get('tmp_root', default_tmp_dir)
        out_archive = os.path.join(tmp_root, 'archive.zip')
        
        with ZipFile(out_archive, mode='w') as zip_out:
            for web_file in web_files:
                if web_file.allowed:
                    full_path = web_file.full_path
                    rel_path = os.path.relpath(full_path, self.directory)
                    
                    zip_out.write(full_path, arcname=rel_path)
            
            zip_out.close()
            
            file_app = FileApp(out_archive)
            get_result = file_app.get(self.environ, start_response)
        
        os.remove(out_archive)
        
        return get_result

    def _build_context(self, allowed_files):
        '''
        Constructs the context required for rendering a Jinja2 template
        '''
        
        # Base URL.
        location = construct_url(
            self.environ,
            with_query_string=False
        )
        
        root = construct_url(
            self.environ,
            with_query_string=False,
            with_path_info=False
        )
        root = root.rstrip('/')
        
        n_allowed, n_forbidden, allowed_size = self.multi_file_handler.file_stats()
        
        context = {
            'environ': self.environ,
            'root': root,
            'location': location,
            'glob': self.glob_string,
            'depth': self.depth,
            'allowed_files': allowed_files,
            'allowed_size': allowed_size,
            'n_allowed': n_allowed,
            'n_forbidden': n_forbidden,
            'version': '.'.join(str(d) for d in __version__)
        }
        
        return context


def validate_glob(glob_string):
    '''
    Checks a glob pattern's structure
    returns a valid glob pattern
    '''
    
    if os.path.sep in glob_string and not glob_string.startswith('*'):
        glob_string = '*' + glob_string
    
    return glob_string


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
        #TODO:
        return None
    
    # Check that the path and application have a common root
    prefix = os.path.commonprefix([path, application_root])
    
    if not prefix == application_root:
        #TODO:
        return None
    
    return path