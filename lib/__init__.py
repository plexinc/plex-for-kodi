from __future__ import absolute_import
import requests

# Disable some warnings. These are not security issue warnings, but alerts to issues that may cause errors
try:
    from requests.packages.urllib3.exceptions import InsecurePlatformWarning, SNIMissingWarning
    requests.packages.urllib3.disable_warnings((InsecurePlatformWarning, SNIMissingWarning))
except:
    import traceback
    traceback.print_exc()

from . import compat
from . import _included_packages
