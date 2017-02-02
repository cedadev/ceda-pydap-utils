'''
Created on 1 Feb 2017

@author: wat
'''

from paste.httpheaders import get_header

CONTENT_TYPE = 'application/zip'

CONTENT_TYPE_HEADER = 'CONTENT_TYPE'
ACCEPT_RANGES_HEADER = 'ACCEPT_RANGES'

CACHE_SIZE = 4096
BLOCK_SIZE = 4096 * 16


class ZipFileApp(object):
    """
    Returns an application that will package the output of an
    os zip command into an iterable file object
    """
    
    def __init__(self, file_object, headers=None, **kwargs):
        self.file_object = file_object
        
        self.headers = []
        
        content_type = get_header(CONTENT_TYPE_HEADER)
        content_type.update(self.headers, 'application/zip')
        
        accept_ranges = get_header(ACCEPT_RANGES_HEADER)
        accept_ranges.update(self.headers, bytes=True)
    
    def get(self, environ, start_response):
        start_response('200 OK', self.headers)
        
        return _FileIter(self.file_object)

class _FileIter(object):

    def __init__(self, file_ref, block_size=None, size=None):
        self.file = file_ref
        self.size = size
        self.block_size = block_size or BLOCK_SIZE

    def __iter__(self):
        return self

    def next(self):
        chunk_size = self.block_size
        if self.size is not None:
            if chunk_size > self.size:
                chunk_size = self.size
            self.size -= chunk_size
        data = self.file.read(chunk_size)
        if not data:
            raise StopIteration
        return data
    __next__ = next

    def close(self):
        self.file.close()

