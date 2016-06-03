import requests
import threading
import urllib
import mimetypes
from xml.etree import ElementTree

import callback
import util


codes = requests.codes
status_codes = requests.status_codes._codes


def GET(*args, **kwargs):
    return requests.get(*args, headers=util.BASE_HEADERS, timeout=util.TIMEOUT, **kwargs)


def POST(*args, **kwargs):
    return requests.post(*args, headers=util.BASE_HEADERS, timeout=util.TIMEOUT, **kwargs)


def Session():
    s = requests.Session()
    s.headers = util.BASE_HEADERS
    s.timeout = util.TIMEOUT

    return s


class RequestContext(dict):
    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, attr, value):
        self[attr] = value


class HttpRequest(object):
    def __init__(self, url, method=None, forceCertificate=False):
        self.hasParams = '?' in url
        self.ignoreResponse = False
        self.session = requests.session()
        self.method = method
        self.url = url
        self.thread = None
        self._cancel = False

        # Use our specific plex.direct CA cert if applicable to improve performance
        # if forceCertificate or url[:5] == "https":  # TODO: ---------------------------------------------------------------------------------IMPLEMENT
        #     certsPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'certs')
        #     if "plex.direct" in url:
        #         self.session.cert = os.path.join(certsPath, 'plex-bundle.crt')
        #     else:
        #         self.session.cert = os.path.join(certsPath, 'ca-bundle.crt')

    def startAsync(self, *args, **kwargs):
        self.logRequest(kwargs.get('body'))
        self.thread = threading.Thread(target=self._startAsync, args=args, kwargs=kwargs)
        self.thread.start()
        return True

    def _startAsync(self, body=None, contentType=None, context=None):
        try:
            if body is not None:
                if not contentType:
                    self.session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
                else:
                    self.session.headers.update({"Content-Type": mimetypes.guess_type(contentType)})

                res = self.session.post(self.url, data=body, timeout=10)
            else:
                res = self.session.get(self.url, timeout=10)

            if self._cancel:
                return
        except Exception, e:
            util.ERROR('Request failed', e)
            return

        self.onResponse(res, context)

    def getToStringWithTimeout(self, seconds=10):
        return self.getPostToStringWithTimeout(seconds)

    def postToStringWithTimeout(self, body=None, seconds=10):
        return self.getPostToStringWithTimeout(seconds, body)

    def getPostToStringWithTimeout(self, seconds=10, body=None):
        # This is a blocking request, so make sure it uses a unique message port
        self.logRequest(body, seconds, False)
        try:
            if body is not None:
                res = self.session.post(self.url, data=body, timeout=seconds)
            else:
                res = self.session.get(self.url, timeout=seconds)

            util.LOG("Got a {0} from {1}".format(res.status_code, self.url))
            # self.event = msg
            return res.text.encode('utf8')
        except Exception, e:
            util.WARN_LOG("Request to {0} errored out after {1} ms: {0}".format(self.url, seconds, e.message))

        return ''

    def getIdentity(self):
        return str(id(self))

    def getUrl(self):
        return self.url

    def cancel(self):
        self._cancel = True

    def addParam(self, encodedName, value):
        if self.hasParams:
            self.url += "&" + encodedName + "=" + urllib.quote(value)
        else:
            self.hasParams = True
            self.url += "?" + encodedName + "=" + urllib.quote(value)

    def addHeader(self, name, value):
        self.session.headers.update({name: value})

    def createRequestContext(self, requestType, callback_=None):
        context = RequestContext()
        context.requestType = requestType

        if callback_:
            context.callback = callback.Callable(self.onResponse)
            context.completionCallback = callback_
            context.callbackCtx = callback_.context

        return context

    def onResponse(self, event, context):
        if context.completionCallback:
            response = HttpResponse(event)
            context.completionCallback(self, response, context)

    def logRequest(self, body, timeout=None, async=True):
        # Log the real request method
        method = self.method
        if not method:
            method = body and "POST" or "GET"
        util.LOG("Starting request: {0} {1} (async={2} timeout={3})".format(method, self.url, async, timeout))


class HttpResponse(object):
    def __init__(self, event):
        self.event = event

    def isSuccess(self):
        if not self.event:
            return False
        return self.event.status_code >= 200 and self.event.status_code < 300

    def isError(self):
        return not self.isSuccess()

    def getStatus(self):
        if not self.event:
            return 0
        return self.event.status_code

    def getBodyString(self):
        if not self.event:
            return ''
        return self.event.text.encode('utf-8')

    def getErrorString(self):
        if not self.event:
            return ''
        return self.event.reason

    def getBodyXml(self):
        if self.event:
            return ElementTree.fromstring(self.getBodyString())

        return None

    def getResponseHeader(self, name):
        if not self.event:
            return None
        return self.event.headers.get(name)


def addRequestHeaders(transferObj, headers=None):
    if isinstance(headers, dict):
        for header in headers:
            transferObj.addHeader(header, headers[header])
            util.DEBUG_LOG("Adding header to {0}: {1}: {2}".format(transferObj, header, headers[header]))


def addUrlParam(url, param):
    return url + ('?' in url and '&' or '?') + param
