# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014-2016 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Handling of proxies."""

import time
import sys
import functools
import subprocess

from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkProxy, QNetworkProxyFactory

from qutebrowser.config import config, configtypes
from qutebrowser.utils import objreg, log, urlutils
from qutebrowser.browser.network import pac


def init():
    """Set the application wide proxy factory."""
    proxy_factory = ProxyFactory()
    objreg.register('proxy-factory', proxy_factory)
    QNetworkProxyFactory.setApplicationProxyFactory(proxy_factory)


class ProxyError(Exception):

    """Exception raised when the proxy process exited."""

    pass


class ProxyProcess:

    """Wrapper over a 'proxy' subprocess.

    Attributes:
        _proc: The subprocess.Popen instance
        error: An error message if an error occurred, or None.
    """

    def __init__(self):
        try:
            self._proc = subprocess.Popen(['proxy'], stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE ,
                                          stdin=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise ProxyError("Failed to start proxy subprocess: {}".format(e))
        self._check_running()
        self.error = None
        print(self._proc.pid)

    def _check_running(self):
        """Make sure the proxy subprocess is still running."""
        status = self._proc.poll()
        if status is not None:
            raise ProxyError("proxy process exited with status {}".format(status))

    @functools.lru_cache()
    def _get_proxies(self, url):
        time.sleep(1)
        url_string = bytes(url.toEncoded(QUrl.RemovePassword)) + b'\n'
        self._proc.stdin.write(url_string)
        self._proc.stdin.flush()
        try:
            proxy_urls = self._proc.stdout.readline().decode('utf-8')
        except UnicodeDecodeError as e:
            raise ProxyError("Failed to decode output: {}".format(e))

        print(proxy_urls)

        proxy_urls = proxy_urls.strip().split()
        log.network.debug("Proxy URLs: {!r}".format(proxy_urls))
        if not proxy_urls:
            raise ProxyError("No proxies returned!")

        proxies = []
        for proxy_url in proxy_urls:
            try:
                proxies.append(urlutils.proxy_from_url(QUrl(proxy_url)))
            except (urlutils.InvalidUrlError, urlutils.InvalidProxyTypeError) as e:
                log.network.error("Failed to parse proxy URL {}".format(proxy_url))

        if not proxy_urls:
            raise ProxyError("No valid proxies returned!")

        return proxies

    def get_proxies(self, url):
        """Get the proxies to be used for the given URL."""
        self.error = None
        try:
            return self._get_proxies(url)
        except ProxyError as e:
            self.error = e
            # .invalid is guaranteed to be inaccessible in RFC 6761.
            # Port 9 is for DISCARD protocol -- DISCARD servers act like
            # /dev/null.
            # Later NetworkManager.createRequest will detect this and display
            # an error message.
            error_host = "pac-resolve-error.qutebrowser.invalid"
            return QNetworkProxy(QNetworkProxy.HttpProxy, error_host, 9)


class ProxyFactory(QNetworkProxyFactory):

    """Factory for proxies to be used by qutebrowser."""

    def __init__(self):
        super().__init__()
        if sys.platform == 'linux':
            self._proxy_process = ProxyProcess()
        else:
            self._proxy_process = None

    def _system_proxy(self, query):
        if self._proxy_process is None:
            return QNetworkProxyFactory.systemProxyForQuery(query)
        return self._proxy_process.get_proxies(query.url())

    def get_error(self):
        """Check if proxy can't be resolved.

        Return:
           None if proxy is correct, otherwise an error message.
        """
        proxy = config.get('network', 'proxy')
        if isinstance(proxy, pac.PACFetcher):
            return proxy.fetch_error()
        elif self._proxy_process is not None:
            return self._proxy_process.error
        else:
            return None

    def queryProxy(self, query):
        """Get the QNetworkProxies for a query.

        Args:
            query: The QNetworkProxyQuery to get a proxy for.

        Return:
            A list of QNetworkProxy objects in order of preference.
        """
        proxy = config.get('network', 'proxy')
        if proxy is configtypes.SYSTEM_PROXY:
            proxies = self._system_proxy(query)
        elif isinstance(proxy, pac.PACFetcher):
            proxies = proxy.resolve(query)
        else:
            proxies = [proxy]
        for p in proxies:
            if p.type() != QNetworkProxy.NoProxy:
                capabilities = p.capabilities()
                if config.get('network', 'proxy-dns-requests'):
                    capabilities |= QNetworkProxy.HostNameLookupCapability
                else:
                    capabilities &= ~QNetworkProxy.HostNameLookupCapability
                p.setCapabilities(capabilities)
        return proxies
