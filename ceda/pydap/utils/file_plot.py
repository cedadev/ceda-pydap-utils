'''
Created on 14 Feb 2017

@author: wat
'''

import os
import io
import nappy
import matplotlib

from enum import Enum

from ceda.pydap.utils.responses import DataPlotApp

matplotlib.use('Agg')
from matplotlib import pyplot
from paste.request import construct_url


class Comparison(Enum):
    """
    Comparison form options
    """
    EQUALS = 'eq'
    GREATER_THAN = 'gt'
    GREATER_EQUAL = 'ge'
    LESS_THAN = 'lt'
    LESS_EQUAL = 'le'


class FilePlotView:
    """
    View for generating NASA Ames file plots
    """
    
    PLOT_FORM_TEMPLATE = 'file_plot.html'
    
    IMG_FORMAT = 'png'
    
    # Default values for matplotlib plot output
    PLOT_STYLE_DEFAULTS = {
        'marker': None,
        'markeredgewidth': 0.5,
        'linestyle': None,
        'linewidth': 0.5,
        'color': 'k'
        
    }
    
    # Mappings for form input processing
    
    MAP_OMIT_CMP = [
        (Comparison.EQUALS.value, '='),
        (Comparison.GREATER_THAN.value, '&gt;'),
        (Comparison.GREATER_EQUAL.value, '&gt;='),
        (Comparison.LESS_THAN.value, '&lt;'),
        (Comparison.LESS_EQUAL.value, '&lt;='),
    ]
    
    MAP_SYMBOL = [
        ('1', 'Plus sign', {'marker': '+'}),
        ('2', 'Circle', {'marker': '.', 'markerfacecolor': 'w'}),
        ('3', 'Period', {'marker': ','}),
        ('4', 'Diamond', {'marker': 'd', 'markerfacecolor': 'w'}),
        ('7', 'X', {'marker': 'x'}),
    ]
    
    MAP_CONNECT = [
        ('y', 'Yes', {'linestyle': None}),
        ('n', 'No', {'linestyle': ' '}),
    ]
    
    # List of possible field ids
    FORM_VARS = [
        'var',
        'xvar',
        'omit_var',
        'omit_cmp',
        'omit_value',
        'ymin',
        'ymax',
        'xmin',
        'xmax',
        'symbol',
        'connect',
    ]
    
    # Form field default values
    FORM_DEFAULTS = {
        'omit_cmp': Comparison.EQUALS.value,
        'symbol': '3',
        'connect': 'y',
    }
    
    def __init__(self, environ, file_path, form):
        """
        Constructor for FilePlotView
        
        @param file_path: path to the NA file
        @param form: dictionary containing a user's input
        """
        
        self.environ = environ
        
        # Validate path
        file_path = validate_path(environ.get('file_root'), file_path)
        self.file_path = file_path
        
        # the map is used when rendering the form
        # template in order to populate options
        self.form_map = {
            'omit_cmp': self.MAP_OMIT_CMP,
            'symbol': self.MAP_SYMBOL,
            'connect': self.MAP_CONNECT,
        }
        
        self.form_defaults = self.FORM_DEFAULTS.copy()
        
        # retrieve variable information from the NA file
        self._parse_variables()
        
        # set form vars using defaults or user-submitted values
        self.form_vars = self._parse_form_vars(form)
    
    def form(self, start_response):
        """
        Construct the plotting UI and return the page from template
        Page contains the user input form and plot output img element
        """
        
        options = {}
        for var_name, var_map in self.form_map.items():
            options[var_name] = self._get_field_values(var_name, var_map)
        
        context = self._build_context(**options)
        template = self.PLOT_FORM_TEMPLATE
        
        return self._render_response(start_response, template, context)
    
    def generate(self, start_response):
        """
        Generate's a plot of the data using input from
        the user's form submission.
        Handles streaming of img reponse to user.
        """
        
        # Define limits each axis
        
        x_limits = None
        xmin = self.form_vars.get('xmin')
        xmax = self.form_vars.get('xmax')
        if xmin and xmax:
            x_limits = [int(xmin), int(xmax)]
        
        y_limits = None
        ymin = self.form_vars.get('ymin')
        ymax = self.form_vars.get('ymax')
        if ymin and ymax:
            y_limits = [int(ymin), int(ymax)]
        
        # Grab canonical variable names from form-submitted keys
        x_var_name = self._translate_form_value('xvar', self.form_vars.get('xvar'))
        y_var_name = self._translate_form_value('var', self.form_vars.get('var'))
        omit_var_name = self._translate_form_value('omit_var', self.form_vars.get('omit_var'))
        
        x_var_miss = []
        y_var_miss = []
        
        # Read the NA file
        na = read_data(self.file_path)
        
        for i in range(na.NV):
            var_name = na.VNAME[i]
            
            # Grab data matching our variable names
            if var_name == x_var_name:
                x_var_miss = [na.VMISS[i]]
                x_var_data = na.V[i]
            if var_name == y_var_name:
                y_var_miss = [na.VMISS[i]]
                y_var_data = na.V[i]
            if var_name == omit_var_name:
                omit_var_data = na.V[i]
        
        # The default X variable is selected separately
        default_x_name = na.XNAME[0]
        if default_x_name == x_var_name:
            x_var_data = na.X
        if default_x_name == y_var_name:
            y_var_data = na.X
        
        try: 
            omit_value = int(self.form_vars.get('omit_value'))
        except TypeError:
            omit_value = self.form_vars.get('omit_value')
        omit_mode = self.form_vars.get('omit_cmp')
        
        # Filter data based on user constraints and file-defined miss values
        x_var_data = list(filter_data(x_var_data, x_var_miss, omit_var_data, omit_value, omit_mode))
        y_var_data = list(filter_data(y_var_data, y_var_miss, omit_var_data, omit_value, omit_mode))
        
        # Cosmetics
        plot_style = self.PLOT_STYLE_DEFAULTS.copy()
        
        symbol = self.form_vars.get('symbol')
        for key, _, style in self.form_map.get('symbol'):
            if key == symbol:
                plot_style.update(style)
        
        connect = self.form_vars.get('connect')
        for key, _, style in self.form_map.get('connect'):
            if key == connect:
                plot_style.update(style)
        
        file_url = construct_url(
            self.environ,
            with_query_string=False
        )
        
        # Generate the plot
        plot = plot_data(na, file_url, x_var_name, x_var_data, y_var_name, y_var_data,
             x_limits=x_limits, y_limits=y_limits, style=plot_style)
        
        file_object = io.BytesIO()
        pyplot.savefig(file_object, format=self.IMG_FORMAT)
        plot.close()
        
        file_object.seek(0)
        
        app = DataPlotApp(file_object)
        
        # Begin response and return plotted graph
        result = app.get(self.environ, start_response)
        return result
    
    def _parse_form_vars(self, form):
        """
        Parse a form to populate form_vars.
        Default values are used if no input is provided.
        """
        form_vars = {}
        
        for key in self.FORM_VARS:
            value = form.get(key)
            if value:
                form_vars[key] = value
            else:
                form_vars[key] = self.form_defaults.get(key)
        
        return form_vars
    
    def _parse_variables(self):
        """
        Reads a NASA Ames file and populates form_map and
        form_defaults based on variable information
        """
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
        self.form_defaults['var'] = '0'
        
        self.form_map['xvar'] = x_map
        self.form_defaults['xvar'] = '-1'
        
        self.form_map['omit_var'] = o_map
        self.form_defaults['omit_var'] = '0'
    
    def _translate_form_value(self, field, input_value):
        """
        Parse user form field input as a key for a field map
        """
        field_map = self.form_map.get(field)
        
        if field_map:
            for key, value in field_map:
                if key == input_value:
                    return value
        
        return None
    
    def _get_field_values(self, field, option_list=None):
        """
        Return template-compatible form information for
        a specific field
        
        @param field: id of the form field
        @param options_list: list of possible options for
                             multiple-select fields
        """
        current_value = self.form_vars.get(field)
        
        if option_list:
            field_values = []
            
            for i in range(len(option_list)):
                option = option_list[i]
                
                if isinstance(option, tuple):
                    field_index, name = option[:2]
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
        """
        Construct a string of HTML parameters from the current form values.
        """
        
        var_string = '?plot=img'
        for key, value in self.form_vars.items():
            if value:
                var_string += ';{}={}'.format(key, value)
        
        return var_string


def read_data(file_path):
    """
    Read data from a NASA Ames file
    """
    
    na_file = nappy.openNAFile(file_path) 
    na_file.readData()
    
    return na_file

def plot_title_info(na, fpath, plt):
    plt.figtext(.5, .95, 'File: %s' % fpath, fontsize=18, ha='center')
    plt.figtext(.5, .9, 'Source: %s' % na.SNAME, fontsize=16, ha='center') 
    plt.figtext(.5, .85, 'Mission: %s' % na.MNAME, fontsize=16, ha='center')

def plot_data(na_obj, fpath, vname1, vdata1, vname2, vdata2,
              x_limits=None, y_limits=None, style={}):
    """
    Draws a graph from the data using a specified style.
    """
    
    pyplot.xlabel(vname1)
    pyplot.ylabel(vname2)
    plot_title_info(na_obj, fpath, pyplot)

    if x_limits: 
        pyplot.xlim(x_limits)
    if y_limits:
        pyplot.ylim(y_limits)
    
    # Point markers with a joined line don't look very nice
    if style.get('marker') == ',' and not style.get('linestyle'):
        style['marker'] = None
    
    pyplot.plot(vdata1, vdata2, **style)
    
    return pyplot

def filter_data(data, forbid_values, omit_data, omit_value, omit_mode=Comparison.EQUALS.value):
    """
    Return an iterator for the dataset with selected outliers nulled
    """
    
    for i in range(len(data)):
        value = data[i]
        
        if value in forbid_values:
            yield None
        elif should_omit(omit_data[i], omit_value, omit_mode):
            yield None
        else:
            yield value

def should_omit(value, omit_value, omit_mode=Comparison.EQUALS.value):
    """
    Compare omit value with chosen omit mode.
    """
    omit = False
    
    if omit_mode == Comparison.EQUALS.value:
        omit = value == omit_value
        
    elif omit_mode == Comparison.GREATER_THAN.value:
        omit = value > omit_value
        
    elif omit_mode == Comparison.GREATER_EQUAL.value:
        omit = value >= omit_value
        
    elif omit_mode == Comparison.LESS_THAN.value:
        omit = value < omit_value
        
    elif omit_mode == Comparison.LESS_EQUAL.value:
        omit = value <= omit_value
    
    return omit

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