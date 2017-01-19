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

# Valid root directory. Only files below this
# directory can be accessed. For security purposes.
VALID_ROOTS = ['/badc', 'neodc']
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
    @param fullname: Full name of file
    """
    
    def __init__(self, file_root, full_path, allowed):
        self.root = file_root
        self.full_path = full_path
        
        self.allowed = allowed
        
        try:
            self.size = self._calculate_size()
        except os.error:
            self.size = 0
    
    def _calculate_size(self):
        return os.path.getsize(self.full_path)


class MultiFileHandler:
    
    def __init__(self, environ, directory, glob_string='*', max_depth='1'):
        assert os.path.isdir(directory)
        self.directory = directory
        
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
        depth = 1
        self._glob_traverse(directory, glob_string, depth)
        
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
    
    def _glob_traverse(self, directory, glob_string, depth):
        
        if depth <= self.max_depth:
            full_glob = os.path.join(directory, glob_string)
            
            # Check user authorisation for directory
            read_allowed = self.file_access.has_access(directory)
            
            for path in glob.iglob(full_glob):
                
                # Check each path to see if we should process it
                if os.path.isfile(path):
                    
                    # Filter out unwanted files - files beginning with '.'  and index.html files
                    filename = os.path.basename(path)
                    if self._is_valid(filename):
                        web_file = WebFile(directory, path, read_allowed)
                        self.files.append(web_file)
                    
                elif os.path.isdir(path):
                    new_depth = depth + 1
                    self._glob_traverse(path, glob_string, new_depth)
    
    def _is_valid(self, filename):
        is_valid = True
        
        if filename.startswith('.') or filename == 'index.html':
            is_valid = False
        
        return is_valid


class MultiFileView:
    
    def __init__(self, environ, directory, glob_string='*', depth=1):
        self.environ = environ
        
        # File specification string
        glob_string = validate_glob(glob_string)
        self.glob_string = glob_string
        
        if depth > MAX_DEPTH:
            depth = MAX_DEPTH
        self.depth = depth
        
        # Validate path
        directory = validate_path(directory)
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
        
        tmp_root = '/home/wat/dev/pydap/multi-file-download/tmp/test/'
        out_archive = tmp_root + 'archive.zip'
        
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
        
        '''TODO:
        #  Tar and gzip the files and dump to standard output. Using an unknown mime
        #  type for the content-type will force users browser to save to disk. 
        #  --exclude option is simply to allow identification of processes started
        #  via mget (sometimes they run on and use lots of cpu).
        print "Content-type: BADCdata\n\n";
        chdir $dirspec;
        my $cmd = "timeout 6000 /usr/bin/nice tar -h --exclude this_is_mget -cf - @filenames | /bin/gzip -c";   
        #   print STDERR "mget cmd: $cmd\n";
        system ("$cmd");
        
        #  Log each file downloaded. Do it after the downloading so we know that the
        #  user has really got it
        for $rfile in (@rdownloads):
            DBrowserUtils::log_file_access ("dbrowser-mget", $rfile, $Cgi);
        '''
        
        return get_result

    def _build_context(self, allowed_files):
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


def write_header(rdirectory):
    """
    Writes html header for download page
    """
    
    print (
        "<<EOT",
        "Content-type: text/html",
        
        "<html>",
        "<head>",
        "<title>",
        "Download selected files",
        "</title>",
        "</head>",
        "<body bgcolor={0}>".format("#ffffff"),
        "<h2>Download selected files</h2>",
        "<hr>",
        "EOT"
    )


def validate_glob(glob_string):
    
    return glob_string
    
    '''TODO:
    if re.match('m/^[\/\w\.\-\+\*\?\[\]]*$/', glob_string):
        # If glob has directory separator then make sure it starts with a '*'
        if re.match('/.*\/.*/', glob_string):
            if not re.match('/^\*/', glob_string):
                glob_string = "*" + glob_string
        
        return glob_string
    else:
        #TODO:
        return None
        (
            "Invalid characters used in match expression $glob<p>",
            "Valid characters are:<p>",
            "* Matches zero or more characters<br>",
            "? Matches any single character<br>",
            "[ ] Matches any of characters specified within brackets<p>",
            "In addition, the / character is used as a directory separator.<p>",
            "For more information, see the help page."
        )
    '''

def validate_path(path):
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
    
    return path
    
    # Check for "../", which could be used to change directory
    
    # Check that file exists
    
    # Remove any trailing slash. ASH 12/11/03
