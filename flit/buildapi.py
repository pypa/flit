from warnings import warn
warn('A package has specified `build-backend = "flit.buildapi"` and is being '
     'built with Flit >= 3.10. This is likely to break in a future version. '
     'Please change the backend to flit_core.buildapi, and/or specify a '
     'maximum version of Flit.')
from flit_core.buildapi import *
