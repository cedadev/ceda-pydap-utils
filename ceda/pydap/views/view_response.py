'''
Created on 21 Feb 2017

@author: wat
'''

from paste.request import construct_url

from pydap.lib import __version__

class ViewResponse(object):
    '''
    Standard response handler for PyDAP utility views
    '''
    
    def __init__(self, environ, start_response):
        '''
        Constructor
        '''
        
        self.environ = environ
        self.start_response = start_response
    
    def _render_response(self, template_file, context, response_code='200 OK'):
        renderer = self.environ.get('pydap.renderer')
        template = renderer.loader(template_file)
        
        content_type = 'text/html'
        output = renderer.render(
            template,
            context,
            output_format=content_type
        )
        
        headers = [('Content-type', content_type)]
        self.start_response(response_code, headers)
        
        return [output.encode('utf-8')]
    
    def _error_response(self, message, code='400 Bad Request', error_template='files_error.html'):
        context = {
            'error_message': message,
            'error_code': code
        }
        
        return self._render_response(error_template, context, code)
    
    def _build_context(self, **kwargs):
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
        
        context = {
            'environ': self.environ,
            'root': root,
            'location': location,
            'version': '.'.join(str(d) for d in __version__)
        }
        
        context.update(kwargs)
        
        return context
