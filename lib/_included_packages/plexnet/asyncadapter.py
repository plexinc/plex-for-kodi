from socket import timeout as SocketTimeout
import socket

from requests.packages.urllib3 import HTTPConnectionPool, HTTPSConnectionPool
from requests.packages.urllib3.poolmanager import PoolManager, proxy_from_url
from requests.adapters import HTTPAdapter
from requests.compat import urlparse
from requests import utils as requests_utils
from requests.packages.urllib3.util import (
    assert_fingerprint,
    resolve_cert_reqs,
    resolve_ssl_version,
    ssl_wrap_socket,
)
from requests.packages.urllib3.exceptions import ConnectTimeoutError
from requests.packages.urllib3.packages.ssl_match_hostname import match_hostname

from httplib import HTTPConnection
import ssl

import util

except_on_missing_scheme = requests_utils.except_on_missing_scheme

DEFAULT_POOLBLOCK = False
SSL_KEYWORDS = ('key_file', 'cert_file', 'cert_reqs', 'ca_certs',
                'ssl_version')


class AsyncVerifiedHTTPSConnection():
    def connect(self):
        util.TEST('xxxxxxxxxxxx')
        # Add certificate verification
        try:
            sock = socket.create_connection(
                address=(self.host, self.port),
                timeout=self.timeout)
        except SocketTimeout:
                raise ConnectTimeoutError(
                    self, "Connection to %s timed out. (connect timeout=%s)" %
                    (self.host, self.timeout))

        resolved_cert_reqs = resolve_cert_reqs(self.cert_reqs)
        resolved_ssl_version = resolve_ssl_version(self.ssl_version)

        if self._tunnel_host:
            self.sock = sock
            # Calls self._set_hostport(), so self.host is
            # self._tunnel_host below.
            self._tunnel()
            self.auto_open = 0

            # The name of the host we're requesting data from.
            actual_host = self._tunnel_host
        else:
            actual_host = self.host

        # Wrap socket using verification with the root certs in
        # trusted_root_certs
        self.sock = ssl_wrap_socket(sock, self.key_file, self.cert_file,
                                    cert_reqs=resolved_cert_reqs,
                                    ca_certs=self.ca_certs,
                                    server_hostname=actual_host,
                                    ssl_version=resolved_ssl_version)

        if resolved_cert_reqs != ssl.CERT_NONE:
            if self.assert_fingerprint:
                assert_fingerprint(self.sock.getpeercert(binary_form=True),
                                   self.assert_fingerprint)
            elif self.assert_hostname is not False:
                match_hostname(self.sock.getpeercert(),
                               self.assert_hostname or actual_host)


class AsyncHTTPConnectionPool(HTTPConnectionPool):
    def _new_conn(self):
        """
        Return a fresh :class:`httplib.HTTPConnection`.
        """
        self.num_connections += 1

        extra_params = {}
        extra_params['strict'] = self.strict

        conn = HTTPConnection(host=self.host, port=self.port,
                              timeout=self.timeout.connect_timeout,
                              **extra_params)

        # Backport fix LP #1412545
        if getattr(conn, '_tunnel_host', None):
            # TODO: Fix tunnel so it doesn't depend on self.sock state.
            conn._tunnel()
            # Mark this connection as not reusable
            conn.auto_open = 0

        return conn


class AsyncHTTPSConnectionPool(HTTPSConnectionPool):
    def _new_conn(self):
        """
        Return a fresh :class:`httplib.HTTPSConnection`.
        """
        self.num_connections += 1

        actual_host = self.host
        actual_port = self.port
        if self.proxy is not None:
            actual_host = self.proxy.host
            actual_port = self.proxy.port

        connection_class = AsyncVerifiedHTTPSConnection

        extra_params = {}
        extra_params['strict'] = self.strict
        connection = connection_class(host=actual_host, port=actual_port,
                                      timeout=self.timeout.connect_timeout,
                                      **extra_params)

        return self._prepare_conn(connection)


pool_classes_by_scheme = {
    'http': AsyncHTTPConnectionPool,
    'https': AsyncHTTPSConnectionPool,
}


class AsyncPoolManager(PoolManager):
    def _new_pool(self, scheme, host, port):
        """
        Create a new :class:`ConnectionPool` based on host, port and scheme.

        This method is used to actually create the connection pools handed out
        by :meth:`connection_from_url` and companion methods. It is intended
        to be overridden for customization.
        """
        pool_cls = pool_classes_by_scheme[scheme]
        kwargs = self.connection_pool_kw
        if scheme == 'http':
            kwargs = self.connection_pool_kw.copy()
            for kw in SSL_KEYWORDS:
                kwargs.pop(kw, None)

        return pool_cls(host, port, **kwargs)


class AsyncHTTPAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=DEFAULT_POOLBLOCK):
        """Initializes a urllib3 PoolManager. This method should not be called
        from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param connections: The number of urllib3 connection pools to cache.
        :param maxsize: The maximum number of connections to save in the pool.
        :param block: Block when no free connections are available.
        """
        # save these values for pickling
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        self.poolmanager = AsyncPoolManager(num_pools=connections, maxsize=maxsize, block=block)

    def get_connection(self, url, proxies=None):
        """Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        """
        proxies = proxies or {}
        proxy = proxies.get(urlparse(url.lower()).scheme)

        if proxy:
            except_on_missing_scheme(proxy)
            proxy_headers = self.proxy_headers(proxy)

            if proxy not in self.proxy_manager:
                self.proxy_manager[proxy] = proxy_from_url(
                    proxy,
                    proxy_headers=proxy_headers,
                    num_pools=self._pool_connections,
                    maxsize=self._pool_maxsize,
                    block=self._pool_block
                )

            conn = self.proxy_manager[proxy].connection_from_url(url)
        else:
            # Only scheme should be lower case
            parsed = urlparse(url)
            url = parsed.geturl()
            conn = self.poolmanager.connection_from_url(url)

        return conn
