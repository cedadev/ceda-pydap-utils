'''
Created on 6 Jan 2017

@author: wat
'''

import os
import re
import gzip
import time

from email.utils import formatdate
from zipfile import ZipFile
from paste.fileapp import FileApp
from paste.request import construct_url
from pydap.lib import __version__

from ceda.pydap.badc.web_page import subtabs, write_badc_header, BCK_COLOR
#from ceda.pydap.badc.web_file import WebFile
from ceda.pydap.badc.user_access_log import log_user_access
from ceda.pydap.db_browser.utils import validate_filespec, commify
from _curses_panel import new_panel
from ceda.pydap.utils.file_access import FileAccess

# Valid root directory. Only files below this
# directory can be accessed. For security purposes.
VALID_ROOT = "/badc"
# Max size (in uncompressed bytes) that can be downloaded
MAX_DOWNLOAD_SIZE = 3000000000
# Maximum number of files to display on a page
MAX_DISPLAY_FILES = 10000
# Maximum directory depth allowed
MAX_DEPTH = 3
# Default extension to be used for gzipped tar files
EXT = ".tgz"

DEFAULT_ACTION = "none"

def main(path_info = None, glob = None, depth = 0, action = DEFAULT_ACTION, url = None):
    
    cgi_glob = glob #File specification string
    if not cgi_glob:
        cgi_glob = "zzz"
    cgi_glob = untaint('.*', cgi_glob)
    cgi_glob = validate_glob(cgi_glob)
    
    cgi_depth = depth
    if not cgi_depth:
        cgi_depth = 1
    if cgi_depth > MAX_DEPTH:
        cgi_depth = MAX_DEPTH
    cgi_depth = untaint('.*', cgi_depth)
    
    # Remove extension to get directory specification. Extension is added so that
    # browsers will choose a sensible filename for the downloaded file
    index = path_info.rfind(EXT)
    cgi_dirspec = None
    if index != -1:
        cgi_dirspec = path_info[0: len(path_info) - len(EXT) ]
    else:
        cgi_dirspec = path_info
    
    # Validate filename
    #
    # 11/10/11 ASH Added access to neodc archive
    dirspec = None
    if re.match('/^\/neodc/', cgi_dirspec):
        dirspec = validate_filespec(cgi_dirspec, "/neodc")
    else:
        dirspec = validate_filespec(cgi_dirspec, VALID_ROOT)
    
    if not dirspec:
        print_page("{0} is an invalid file specification".format(cgi_dirspec))
    
    log_user_access(id = "mget", info = "glob={0} dir={1}".format(cgi_glob, dirspec), logAll = 0)
    
    # Construct file object for given directory specification
    rdir = WebFile(dirspec, None)
    
    # Check if access is allowed for this directory
    #if ($rdir->read_authorised){
    if True: #TODO: (NDG::Security::Weblogon::read_authorised($rdir->fullname)):
        if action.lower() == "download":
            download_files(rdir, cgi_glob, cgi_depth)
        else:
            list_download_files(rdir, cgi_glob, cgi_depth)
        
    else:
        print_page ("You are not authorised to access directory {0}".format(dirspec))


def list_download_files(environ, start_response, directory, glob, depth):
    """
    Returns a view listing information about files to be downloaded
    """
    
    files = identify_files(environ, directory, glob, depth)
    
    allowed_files = []
    n_allowed, n_forbidden, allowed_size = selected_file_stats(files)
    
    for web_file in files:
        if web_file.allowed:
            file_path = web_file.full_path
            
            relative_path = ".{0}{1}".format(
                os.path.sep,
                os.path.relpath(file_path, directory)
            )
            
            file_details = {
                'relative_path': relative_path,
                'size': web_file.size
            }
            
            allowed_files.append(file_details)
    
    # Base URL.
    location = construct_url(environ, with_query_string=False)
    root = construct_url(environ, with_query_string=False, with_path_info=False).rstrip('/')
    
    context = {
        'environ': environ,
        'root': root,
        'location': location,
        'glob': glob,
        'depth': depth,
        'allowed_files': allowed_files,
        'allowed_size': allowed_size,
        'n_allowed': n_allowed,
        'n_forbidden': n_forbidden,
        'version': '.'.join(str(d) for d in __version__)
    }
    
    renderer = environ.get('pydap.renderer')
    template = renderer.loader('selected_files.html')
    
    content_type = 'text/html'
    output = renderer.render(template, context, output_format=content_type)
    
    headers = [('Content-type', content_type)]
    start_response("200 OK", headers)
    
    return [output.encode('utf-8')]
    
    '''
    directory = rdirectory.fullname
    
    write_header(rdirectory)
    
    rfiles = identify_files(rdirectory, glob, depth)
    nAllowed, nForbidden, allowedSize = selected_file_stats(rfiles)
    
    print "<TABLE>\n"
    print "<TR><TD><B>Filespec:<TD>$glob\n"
    print "<TR><TD><B>Depth:<TD>$depth\n"
    
    print "<!-- Glob: \"$glob\" -->\n"
    
    print "<TR><TD><B>Files selected for download:</B><TD>$nAllowed\n"
    
    
    print (
        "<TR><TD><B>Total size of selected files (bytes):</B><TD>"
        "{0} ({1})\n".format(commify(allowedSize), allowedSize)
    )
    print "<TR><TD><B>Files you are not authorised to access:</B><TD>$nForbidden\n"
    print "</TABLE>\n"
    
    if allowedSize <= MAX_DOWNLOAD_SIZE:
    
        if nAllowed > 0:
            print "<form method=\"get\"> <center>\n"
            print "<input type=\"hidden\" name=\"glob\" value=\"$glob\">\n"
            print "<input type=\"hidden\" name=\"depth\" value=\"$depth\">\n"
            print "<input name=\"action\" value=\"Download\" type=\"submit\">\n"
            print "</center></form>"
    
    else:
        print "<p><b>\n"
        print ("Sorry, you can only download up to ",
            "{0} bytes. ".format(commify(MAX_DOWNLOAD_SIZE)),
            "Please reduce your selection and try again.",
            "You may find that <a href=\"/help/ftp_guide.html\">FTP</a> is a more convenient way of downloading this data.",
            "<p>\n")
        print "</b>\n"
    
    print "<HR><P>\n"
    print "<em>Details of files selected for downloading:</em><P>\n"
    print "<TABLE>\n"
    print "<TH>File</TH><TH></TH><TH>Size (bytes)</TH>\n"
    
    ndisplay = rfiles[-1] + 1
    if ndisplay > MAX_DISPLAY_FILES:
        ndisplay = MAX_DISPLAY_FILES
    
    for n in range(0, ndisplay):
        
        rfile = rfiles[n]
        print "<TR>\n"
        
        ## my ($access, $access_type) = $rfile->read_authorised;
        access = None #TODO: NDG::Security::Weblogon::read_authorised($rfile->fullname);
        
        # Remove directory specifcation from full path of file.
        file = rfile.fullname
        
        if depth > 1:
            file = re.match('s/^$directory[\/]?/\.\//', file)
        else:
            file = re.match('s/^$directory[\/]?//', file)
        
        if access:
            print "<TD>", file, "</TD>\n"
            print "<TD WIDTH=\"10\"></TD>\n"
            print "<TD ALIGN=\"right\">{0}</TD>\n".format(commify(rfile.size))
        else:
            print "<TD><font color=\"red\">", file, "</font></TD>\n"
            print "<TD WIDTH=\"10\"></TD>\n"
            print "<TD ALIGN=\"center\"><font color=\"red\">-</font></TD>\n"
            print "<TD><font color=\"red\"><B>Access denied!</B></font></TD>\n"
        
        print "</TR>\n"
    
    print "</TABLE>\n"
    print "</body>\n</html>\n"
    '''


def download_files(environ, start_response, directory, glob, depth):
    """
    Downloads the requested set of files as a single gzipped-tar file
    
    @param directory: Reference to path of the active directory
    @param glob: Filename glob specifying files to be downloaded
    """
    
    file_paths = identify_files(environ, directory, glob, depth)
    
    with gzip.open(file_paths[0], 'rb') as f:
        file_content = f.read()
        
        tmp_root = '/home/wat/dev/pydap/multi-file-download/tmp/test/'
        
        in_files = ['f1', 'f2', 'f3']
        out_archive = tmp_root + 'archive.zip'
        
        with ZipFile(out_archive, mode='w') as zip_out:
            for f in in_files:
                zip_out.write(tmp_root + f, arcname=f)
        
        return FileApp(out_archive)(environ, start_response)
    
    '''TODO:
    rfiles = identify_files(rdir, glob, depth)
    
    # Check total size of files and exit with error message if too big
    nAllowed, nForbidden, allowedSize = selected_file_stats(rfiles)
    if allowedSize > MAX_DOWNLOAD_SIZE:
        print_page ("Too big!")
    
    if rfiles:
        #  Construct list of file references for files which can be downloaded - exclude
        #  files to which the user does not have access
        rdownloads = []
        
        for rfile in rfiles:
            ##    my ($access, $access_type) = $rfile->read_authorised;  
            access = NDG::Security::Weblogon::read_authorised($rfile->fullname);
            
            if access:
                rdownloads.append(rfile)
        
        #  Construct list of filenames of files to be downloaded. Do not include path
        #  specification to avoid problems when extracting files.
        filenames = []
        directory = rdir.fullname
        
        for rfile in rdownloads:
            file = rfile.fullname
            file = re.match('s/^$directory[\/]?/\.\//', file)
            
            filenames.append(file)
        
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


class WebFile:
    """
    @param fullname: Full name of file
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


def identify_files(environ, directory, glob, depth):
    """
    Returns a list of WebFile object references for the files which have been 
    selected to download. This list includes files for which the user does not
    have read permission, so this needs to be checked before downloading the
    files.
    
    Note that I have made some changes to this routine to increace the speed when
    the directory contains a large number of files. In particular I perform a
    specific test for each filename, rather than using generalised grep statements
    to weed out the files which are not required.
    
    @param rdirectory: Directory containing files to be selected
    @param glob: glob containing specification for files to be downloaded
    @param depth: How many directories to go down
    """
    
    files = []
    
    assert os.path.isdir(directory)
    max_depth = directory.count(os.path.sep) + (depth - 1)
    
    # Retrieve all files in directory
    for root, dirnames, filenames in os.walk(directory):
        
        new_depth = root.count(os.path.sep)
        if max_depth <= new_depth:
            del dirnames[:]
        
        # Check user authorisation
        file_access = FileAccess(environ.get('file_root'), root)
        read_allowed = file_access.check_authorisation(environ, root)
        
        # Check each file to see if we should process it
        for filename in filenames:
            full_path = root + os.path.sep + filename
            #TODO:
            #if re.match(glob, filename):
            
            #TODO:
            # Filter out unwanted files - files beginning with '.'  and index.html files
            
            web_file = WebFile(full_path, read_allowed)
            files.append(web_file)
    
    return files
    
    '''TODO:
    # Get list of all files in directory
    directory = rdirectory.fullname
    cmd = None
    
    if re.match('/.*\/.*/', glob):
        cmd = "/usr/bin/find $directory -follow -path '$glob' -maxdepth $depth"
    else:
        cmd = "/usr/bin/find $directory -follow -name '$glob' -maxdepth $depth"
    
    ##print STDERR "mget cmd: $cmd\n";
    
    my @files =  `$cmd`;
    chop @files;
    
    # Sort files - they don't always seem to come back in the right order
    @files = sort(@files);
    
    # Compile regular expression to untaint filename
    my $rx =  '^(.*)$';
    my $untaint_regx = qr/$rx/;
    
    # Check each file to see if we should process it. If so then create a WebFile
    # object and add to list
    for $file in (@files):
        
        if ( -f $file): #Process only 'plain' files
            # Untaint the filename
            $file =~ $untaint_regx;
            $file = $1;
            
            my $rfile = BADC::WebFile->new($file);
            
            # Filter out unwanted files - files beginning with '.'  and index.html files
            if ( (substr($rfile->name,0,1) ne '.') && ($rfile->name ne "index.html") ):
                push @rfiles, $rfile;
    '''


def selected_file_stats(files):
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
    
    for web_file in files:
        
        if web_file.allowed:
            n_allowed += 1
            allowed_size += web_file.size
        else:
            n_forbidden += 1
    
    return (n_allowed, n_forbidden, allowed_size)


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
        "<body bgcolor={0}>".format(BCK_COLOR),
        "<h2>Download selected files</h2>",
        "<hr>",
        "EOT"
    )


def print_page(msg):
    """
    Prints the given text on a html page and exits
    """
    
    write_badc_header("", "")
    print "<p>\n"
    print "$msg\n"
    print "<p>\n"
    
    # Write page footer. 
    print "<p>\n";
    
    host = ""
    footer = [
        "<a class=menu HREF=\"{0}/\">Home</a>".format(host),
        "&nbsp;&nbsp;&nbsp;\n",
        "<a class=menu HREF=\"{0}/help/contact.html\">Contact</a>".format(host),
        "&nbsp;&nbsp;&nbsp;\n",
        "<a class=menu HREF=\"{0}/conditions/badc_anon.html\">Disclaimer</a>".format(host),
        "&nbsp;&nbsp;&nbsp;\n",
        '<div class=lastm>Last Modified: <script>document.write(document.lastModified);</script></div>',
        "\n"
    ]
    footer = subtabs(0, "bottom", footer);
    print footer, "\n"
    
    print "</body>\n</html>\n"
    
    return None


def untaint(exp, values):
    """
    Checks the given values using the given regular expression. If successful then
    returns untainted copy of value with any leading or trailing blanks removed.
    If unsuccessful then dies with error message.
    
    @param exp: Regular expression containing valids
    @param values: Value(s) to be checked
    """
    
    for val in values:
        if val:
            result = re.match('m/^\s*($exp)\s*$/', val)
            if result:
                val = result.group(0)
                val = re.match('s/\s+$//', val) #Make sure trailing blanks have been removed
            else:
                print_page(("Invalid characters used", "Invalid charaters found in string '$val'"))
            
            wantarray = True
            if wantarray:
                return values
            else:
                return values[0]


def validate_glob(glob):
    
    if re.match('m/^[\/\w\.\-\+\*\?\[\]]*$/', glob):
        # If glob has directory sepearator then make sure it starts with a '*'
        if re.match('/.*\/.*/', glob):
            if not re.match('/^\*/', glob):
                glob = "*" + glob
        
        return glob
    else:
        return print_page(
            (
                "Invalid characters used in match expression $glob<p>",
                "Valid characters are:<p>",
                "* Matches zero or more characters<br>",
                "? Matches any single character<br>",
                "[ ] Matches any of characters specified within brackets<p>",
                "In addition, the / character is used as a directory separator.<p>",
                "For more information, see the help page."
            )
        )
