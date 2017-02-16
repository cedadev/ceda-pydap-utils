'''
Created on 14 Feb 2017

@author: wat
'''

import os
import io
import nappy
import matplotlib

from ceda.pydap.utils.responses import DataPlotApp

matplotlib.use('Agg')
from matplotlib import pyplot
from paste.request import construct_url


class FilePlotView:
    """
    
    """
    
    IMG_FORMAT = 'png'
    
    MAP_OMIT_CMP = [
        ('eq', '='),
        ('gt', '&gt;'),
        ('ge', '&gt;='),
        ('lt', '&lt;'),
        ('le', '&lt;='),
    ]
    
    MAP_SYMBOL = [
        ('1', 'Plus sign'),
        ('2', 'Asterisk'),
        ('3', 'Period'),
        ('4', 'Diamond'),
        ('7', 'X'),
    ]
    
    MAP_CONNECT = [
        ('y', 'Yes'),
        ('n', 'No'),
    ]
    
    def __init__(self, environ, file_path, form):
        self.environ = environ
        
        # Validate path
        file_path = validate_path(environ.get('file_root'), file_path)
        self.file_path = file_path
        
        self.form_map = {
            'var': None,
            'xvar': None,
            'omit_var': None,
            'omit_cmp': self.MAP_OMIT_CMP,
            'omit_value': None,
            'ymin': None,
            'ymax': None,
            'xmin': None,
            'xmax': None,
            'symbol': self.MAP_SYMBOL,
            'connect': self.MAP_CONNECT,
        }
        
        self.form_vars = self._parse_form_vars(form)
        self._map_variables()
    
    def form(self, start_response):
        """
        
        """
        
        options = {}
        for var_name, var_map in self.form_map.items():
            options[var_name] = self._get_field_values(var_name, var_map)
        
        context = self._build_context(**options)
        template = 'file_plot.html'
        
        return self._render_response(start_response, template, context)
    
    def generate(self, start_response):
        """
        
        """
        
        x_limits = None
        xmin = self.form_vars.get('xmin')
        xmax = self.form_vars.get('xmax')
        if xmin and xmax:
            x_limits = [int(xmax), int(xmin)]
        
        y_limits = None
        ymin = self.form_vars.get('ymin')
        ymax = self.form_vars.get('ymax')
        if ymin and ymax:
            y_limits = [int(ymax), int(ymin)]
        
        x_var_name = self._translate_form_value('xvar', self.form_vars.get('xvar'))
        y_var_name = self._translate_form_value('var', self.form_vars.get('var'))
        
        x_var_miss = []
        y_var_miss = []
        
        marker = None
        
        na = read_data(self.file_path)
        
        for i in range(na.NV):
            var_name = na.VNAME[i]
            
            if var_name == x_var_name:
                x_var_miss = [na.VMISS[i]]
                x_var_data = na.V[i]
            if var_name == y_var_name:
                y_var_miss = [na.VMISS[i]]
                y_var_data = na.V[i]
        
        default_x_name = na.XNAME[0]
        if default_x_name == x_var_name:
            x_var_data = na.X
        if default_x_name == y_var_name:
            y_var_data = na.X
        
        x_var_data = list(filter_miss_values(x_var_data, x_var_miss))
        y_var_data = list(filter_miss_values(y_var_data, y_var_miss))
        
        file_url = construct_url(
            self.environ,
            with_query_string=False
        )
        
        plot = plot_data(na, file_url, x_var_name, x_var_data, y_var_name, y_var_data,
             x_limits=x_limits, y_limits=y_limits, marker=marker)
        
        file_object = io.BytesIO()
        pyplot.savefig(file_object, format=self.IMG_FORMAT)
        plot.close()
        
        file_object.seek(0)
        
        app = DataPlotApp(file_object)
        
        # Begin response and return plotted graph
        result = app.get(self.environ, start_response)
        return result
    
    def _parse_form_vars(self, form):
        
        form_vars = {}
        
        for key in self.form_map.keys():
            value = form.get(key)
            if value:
                form_vars[key] = value
        
        return form_vars
    
    def _map_variables(self):
        
        na = read_data(self.file_path)
        
        y_map = []
        x_map = []
        o_map = []
        
        x_map.append(('-1', na.XNAME[0]))
        
        for i in range(len(na.VNAME)):
            var_name = na.VNAME[i]
            mapping = (str(i), var_name)
            
            y_map.append(mapping)
            x_map.append(mapping)
            o_map.append(mapping)
        
        y_map.append(('-2', na.XNAME[0]))
        
        self.form_map['var'] = y_map
        self.form_map['xvar'] = x_map
        self.form_map['omit_var'] = o_map
    
    def _translate_form_value(self, field, input_value):
        field_map = self.form_map.get(field)
        
        if field_map:
            for key, value in field_map:
                if key == input_value:
                    return value
        
        return None
    
    def _get_field_values(self, field, option_list=None):
        current_value = self.form_vars.get(field)
        
        if option_list:
            field_values = []
            
            for i in range(len(option_list)):
                option = option_list[i]
                
                if isinstance(option, tuple):
                    field_index, name = option
                else:
                    field_index = i
                    name = option
                
                selected = field_index == current_value
                
                field_values.append((field_index, name, selected))
        else:
            if current_value:
                field_values = current_value
            else:
                field_values = ''
        
        return field_values
    
    def _render_response(self, start_response, template_file, context, response_code='200 OK'):
        renderer = self.environ.get('pydap.renderer')
        template = renderer.loader(template_file)
        
        content_type = 'text/html'
        output = renderer.render(
            template,
            context,
            output_format=content_type
        )
        
        headers = [('Content-type', content_type)]
        start_response(response_code, headers)
        
        return [output.encode('utf-8')]
    
    def _error_response(self, start_response, message, code = '400 Bad Request'):
        context = {
            'error_message': message,
            'error_code': code
        }
        
        return self._render_response(start_response, 'files_error.html', context, code)
    
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
        
        file_name = os.path.basename(self.file_path)
        
        img_url = location + self._build_img_vars()
        
        context = {
            'environ': self.environ,
            'root': root,
            'location': location,
            'file_name': file_name,
            'img_url': img_url,
        }
        
        context.update(kwargs)
        
        return context
    
    def _build_img_vars(self):
        
        var_string = '?plot=img'
        for key, value in self.form_vars.items():
            if value:
                var_string += ';{}={}'.format(key, value)
        
        return var_string


def read_data(file_path):
    na_file = nappy.openNAFile(file_path) 
    na_file.readData()
    
    return na_file

def plot_title_info(na, fpath, plt):
    plt.figtext(.5, .95, 'File: %s' % fpath, fontsize=18, ha='center')
    plt.figtext(.5, .9, 'Source: %s' % na.SNAME, fontsize=16, ha='center') 
    plt.figtext(.5, .85, 'Mission: %s' % na.MNAME, fontsize=16, ha='center')

def plot_data(na_obj, fpath, vname1, vdata1, vname2, vdata2,
              x_limits=None, y_limits=None, marker=None):
    pyplot.xlabel(vname1)
    pyplot.ylabel(vname2)
    plot_title_info(na_obj, fpath, pyplot)

    if x_limits: 
        pyplot.xlim(x_limits)
    if y_limits:
        pyplot.ylim(y_limits)

    if not marker: marker = 'r'
    pyplot.plot(vdata1, vdata2, marker)
    
    return pyplot

def filter_miss_values(data, miss_values):
    for point in data:
        if not point in miss_values:
            yield point
        else:
            yield None

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
        raise ValueError('Path does not exist')
    
    # Check that the path and application have a common root
    prefix = os.path.commonprefix([path, application_root])
    
    if not prefix == application_root:
        raise ValueError('Path root does not match application root')
    
    return path
