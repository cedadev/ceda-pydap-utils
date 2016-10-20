# CEDA PyDAP Utils
CEDA-specific functionality for a PyDAP (https://github.com/pydap/pydap) server.

## Releases
- 0.2.0:
 - Added support for Jinja2 rendering of custom PyDAP templates.
 - Added templatetags package containing utility functions for templates.
 - Jinja2 is now a requirement.
- 0.1.0:
 - Extended functionality of pydap.wsgi.file.FileServer to hide directories
   depending on the content of their README file.
 - Added a utility function for retrieving the first line of an archive README
   file
