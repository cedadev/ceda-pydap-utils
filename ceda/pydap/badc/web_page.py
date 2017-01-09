'''
Created on 5 Jan 2017

@author: wat
'''

import re

BCK_COLOR = "#ffffff" #Page background color 
BCK_DARK  = "#003399" #Background color, as used on home page (dark blue)
HI_COLOR  = "#ADD8E6" #Highlight color (light blue)

CSS = "/styles/menu.new.css" #Standard BADC stylesheet

def getheader(tabSection = "data"):
    file = ""
    host = ""
    
    selecttab = 0
    docroot = "/var/www/badc_site/htdocs"
    
    # if file is not a absolute path then it is from a CGI proggrame.
    # It is a tab name and needs the docroot adding.
    if re.match('!~ /^\//', file):
        file = "{0}/{1}".format(docroot, file)
    
    # define the content of the menu tabs
    tabtext = ["<A class=menu  HREF=\"$host/home/\"><IMG border=\"0\" align=\"middle\" SRC=\"/graphics/logos/badc-logo-onlb-30.gif\">Home</A>", 
        "<A class=menu  HREF=\"$host/mybadc\">My&nbsp;BADC</A>", 
        "<A class=menu  HREF=\"$host/data/\">Data</A>",
        "<A class=menu  HREF=\"$host/search/\">Search</A>",
        "<A class=menu  HREF=\"$host/community/\">Community</A>",
        "<A class=menu  HREF=\"$host/help/\">Help</A>"
    ]
    # define the content of selected tabs
    stabtext = ["<A class=menu  HREF=\"$host/home/\"><IMG border=\"0\" align=\"middle\" SRC=\"/graphics/logos/badc-logo-onblue-30.gif\">Home</A>", 
        "<A class=menu  HREF=\"$host/mybadc\">My&nbsp;BADC</A>", 
        "<A class=menu  HREF=\"$host/data/\">Data</A>",
        "<A class=menu  HREF=\"$host/search/\">Search</A>",
        "<A class=menu  HREF=\"$host/community/\">Community</A>",
        "<A class=menu  HREF=\"$host/help/\">Help</A>"
    ]
    # define the names of the tabs - these are the names of subdirectories
    # from the document root.
    tabnames = ["home",
            "reg",
            "data",
            "search",
            "community",
            "help"
    ]
    ntabs = tabnames
    
    # find the selected tab from the filename
    for i in range(0, ntabs):
        if re.match('/{0}\/{1}/'.format(docroot, tabnames[i]), file):
            selecttab = i;
            tabtext[i] = stabtext[i]; # copy the selected tab text into tab text.
    
    header = ""
    
    '''#TODO:
    # open the submenu file and read html fragments into an array  
    open(STAB, "$docroot/$tabnames[$selecttab]/tabs.txt"); my @subtabtext=<STAB>; close STAB;    
    
    for my $tab (@subtabtext) {
    $tab =~ s/href\=\"/href\=\"$host/i;
    }
    # make header from tabtext and  and subtabtext        
    my $header =  tabs($selecttab,@tabtext);
    $header .= subtabs($selecttab,'top',@subtabtext);
    '''
    
    return header;


def write_badc_header(title, headerline, tabSection = "data"):
    """
    Writes html header for page containing BADC logo at top
    
    @param tabSection: tab section to select: 'data', 'search' etc.
    """
    
    PREFIX = "File downloader"
    
    if not title:
        title = PREFIX
    
    # Writes BADC page header with the new menu.
    print "Content-type: text/html\n"
    if headerline:
        print "$opts{headerline}\n"
    print "\n"
    
    print "<html>\n"
    print "<head>\n"
    print "<title>$title</title>\n"
    
    css = "/styles/menu.new.css"
    link = "<link rel=\"stylesheet\" type=\"text/css\" href=\"$css\">\n"
    print link
    
    print "</head>\n"
    print "<body>\n"
    print getheader(tabSection)
    print "<h1>$title</h1>\n"
    return None #TODO: BADC::Webpage::page_head ($title, $headline)


def subtabs(seltab, topOrbot, tabtext):
    
    if not topOrbot:
        topORbot = "bottom"
    
    tabs = '<TABLE width="100%" height="25" BORDER="0" CELLSPACING="0" '
    tabs = " CELLPADDING=\"0\"><TR>"
    tabs = " <TD BGCOLOR=\"#333399\"><IMG SRC=\"/graphics/tabs/${topORbot}left.jpg\"></TD>"
    for tab in tabtext:
        tabs = (' <TD BGCOLOR="#333399">', tab, '</TD>')
    
    tabs = " <TD WIDTH=\"10\" bgcolor=\"#333399\" align=\"right\"><IMG SRC=\"/graphics/tabs/${topORbot}right.jpg\"></TD>"
    tabs = ' </TR></TABLE>'
    
    return tabs
