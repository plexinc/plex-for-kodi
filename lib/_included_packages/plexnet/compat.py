# -*- coding: utf-8 -*-
"""
Python 2/3 compatability
Always try Py3 first
"""

from __future__ import absolute_import
try:
    from urllib.parse import urlencode
except ImportError:
    from six.moves.urllib.parse import urlencode

try:
    from urllib.parse import quote
except ImportError:
    from six.moves.urllib.parse import quote

try:
    from urllib.parse import quote_plus
except ImportError:
    from six.moves.urllib.parse import quote_plus

try:
    from configparser import ConfigParser
except ImportError:
    from six.moves.configparser import ConfigParser
