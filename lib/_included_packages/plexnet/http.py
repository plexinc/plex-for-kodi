import requests

import util


codes = requests.codes
status_codes = requests.status_codes


def GET(*args, **kwargs):
    return requests.get(*args, headers=util.BASE_HEADERS, timeout=util.TIMEOUT, **kwargs)


def POST(*args, **kwargs):
    return requests.post(*args, headers=util.BASE_HEADERS, timeout=util.TIMEOUT, **kwargs)


def Session():
    s = requests.Session()
    s.headers = util.BASE_HEADERS
    s.timeout = util.TIMEOUT

    return s
