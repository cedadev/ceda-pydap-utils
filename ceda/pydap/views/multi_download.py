'''
Created on 6 Jan 2017

@author: wat
'''

import os
import glob
import subprocess

import logging
from ceda.pydap.views.view_response import ViewResponse
from ceda.pydap.utils.file.path_utils import validate_path
from ceda.pydap.utils.action_log import format_action_message
logger = logging.getLogger(__name__)

from paste.request import construct_url

from ceda.pydap.utils.file.file_access import FileAccess
from ceda.pydap.views.response.response import ZipFileApp

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
    
    def __lt__(self, other):
        return self.full_path.__lt__(other.full_path)


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
            
            parts = filter(None, glob_string.split(os.path.sep))
            
            # Add missing glob parts according to max depth
            num_missing = self.max_depth - len(parts) - current_depth + 1
            for _ in range(num_missing):
                parts.append('*')
            
            # Grab the left-most glob expression and reimainder
            current_glob = parts[0]
            parts = parts[1:]
            remaining_glob = os.path.sep.join(parts)
            
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


class MultiFileView(ViewResponse):
    '''
    Class for serving different multi-file download views
    using a Jinja2 template engine and a MultiFileHandler.
    '''
    
    def __init__(self, environ, start_response, directory, glob_string='*', depth=1):
        
        super(MultiFileView, self).__init__(environ, start_response)
        
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
    
    def list_files(self):
        """
        Returns a view listing information about files to be downloaded
        """
        
        # Log action
        logger.info(
            format_action_message(
                self.environ,
                'MultiFileView.list_files',
                'listing files with glob "{}"'.format(self.glob_string)
            )
        )
        
        web_files = self.multi_file_handler.files
        web_files = sorted(web_files)
        
        n_files = 0
        allowed_files = []
        over_size_limit = False
        for web_file in web_files:
            n_files += 1
            if n_files >= MAX_DISPLAY_FILES:
                over_size_limit = True
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
        
        context = self._build_context()
        
        n_allowed, n_forbidden, allowed_size = self.multi_file_handler.file_stats()
        if allowed_size > MAX_DOWNLOAD_SIZE:
            over_size_limit = True
        
        context.update({
            'glob': self.glob_string,
            'depth': self.depth,
            'allowed_size': allowed_size,
            'n_allowed': n_allowed,
            'n_forbidden': n_forbidden,
            'allowed_files': allowed_files,
            'over_size_limit': over_size_limit,
            'MAX_DOWNLOAD_SIZE': MAX_DOWNLOAD_SIZE
        })
        template = 'selected_files.html'
        
        return self._render_response(template, context)
    
    def download_files(self):
        """
        Downloads the requested set of files as a single gzipped-tar file
        
        @param directory: Reference to path of the active directory
        @param glob: Filename glob specifying files to be downloaded
        """
        
        # Log action
        logger.info(
            format_action_message(
                self.environ,
                'MultiFileView.download_files',
                'downloading files with glob "{}"'.format(self.glob_string)
            )
        )
        
        # Check total size of files and exit with error message if too big
        _, _, allowed_size = self.multi_file_handler.file_stats()
        if allowed_size > MAX_DOWNLOAD_SIZE:
            error_message = "Max file size exceeded."
            return self._error_response(error_message)
        
        web_files = self.multi_file_handler.files
        
        # Compose subprocess command for generating a zip
        cmd = ['timeout', '6000', 'nice', 'zip', '-Z', 'store', '-b', '-O', '-']
        base_path = self.directory
        for web_file in web_files:
            filename = os.path.relpath(web_file.full_path, base_path)
            cmd.append(filename)
        
        # Generate an response from the command
        pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=base_path)
        out = pipe.stdout
        app = ZipFileApp(out)
        
        # Begin response and return iterable file object
        result = app.get(self.environ, self.start_response)
        return result


def validate_glob(glob_string):
    '''
    Checks a glob pattern's structure
    returns a valid glob pattern
    '''
    
    if os.path.sep in glob_string and not glob_string.startswith('*'):
        glob_string = '*' + glob_string
    
    return glob_string
