# -*- coding: utf-8 -*-
import http
from threading import Thread
from xml.etree import ElementTree
import time

import exceptions

import video
import audio
import photo

video, audio, photo  # Hides warning message


class PinLogin(object):
    INIT = 'https://my.plexapp.com/pins.xml'
    POLL = 'https://my.plexapp.com/pins/{0}.xml'
    POLL_INTERVAL = 1

    def __init__(self, callback=None):
        self._callback = callback
        self.id = None
        self.pin = None
        self.authenticationToken = None
        self._finished = False
        self._abort = False
        self._expired = False
        self._init()

    def _init(self):
        response = http.POST(self.INIT)
        if response.status_code != http.codes.created:
            codename = http.status_codes.get(response.status_code)[0]
            raise exceptions.BadRequest('({0}) {1}'.format(response.status_code, codename))
        data = ElementTree.fromstring(response.text.encode('utf-8'))
        self.pin = data.find('code').text
        self.id = data.find('id').text

    def _poll(self):
        try:
            start = time.time()
            while not self._abort and time.time() - start < 300:
                response = http.GET(self.POLL.format(self.id))
                if response.status_code != http.codes.ok:
                    self._expired = True
                    break
                data = ElementTree.fromstring(response.text.encode('utf-8'))
                token = data.find('auth_token').text
                if token:
                    self.authenticationToken = token
                    break
                time.sleep(self.POLL_INTERVAL)

            if self._callback:
                self._callback(self.authenticationToken)
        finally:
            self._finished = True

    def finished(self):
        return self._finished

    def expired(self):
        return self._expired

    def startTokenPolling(self):
        t = Thread(target=self._poll, name='PIN-LOGIN:Token-Poll')
        t.start()
        return t

    def waitForToken(self):
        t = self.startTokenPolling()
        t.join()
        return self.authenticationToken

    def abort(self):
        self._abort = True
