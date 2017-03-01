'''
Created on 1 Mar 2017

@author: wat
'''

import re

def is_nasa_ames(file_path):
    """
    Checks if given file is a NASA Ames file. Returns boolean
    """
    
    # Ignore HADISST files, which have a first line that looks like a NASA-Ames file
    if re.match('.*\/ukmo-hadisst\/data\/.*', file_path):
        return False
    
    try:
        with open(file_path) as na_file:
            line = na_file.readline()
            
            if re.match('^\s*\d+\s+(\d{4})\s*$', line):
                return True
            else:
                return False
            
    except IOError:
        return False
