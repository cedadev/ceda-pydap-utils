'''
Created on 24 Feb 2017

@author: wat
'''

ENCODINGS = [
    'utf-8',
    'iso-8859-1',
]

def decode_multi(encoded_string, encodings=ENCODINGS):
    """
    Attempts to decode an input string using
    a number of different encoding types
    """
    
    decoded_string = None
    for encoding in encodings:
        try:
            decoded_string = encoded_string.decode(encoding)
        except UnicodeDecodeError:
            pass
        
        if decoded_string:
            return decoded_string
