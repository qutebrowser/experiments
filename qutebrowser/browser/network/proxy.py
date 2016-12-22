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


@functools.lru_cache()
def _system_proxy_subprocess(url):
    if sys.platform != 'linux':
        return []

    url_string = url.toString(QUrl.FullyEncoded | QUrl.RemovePassword)
    try:
        proxy_urls = subprocess.check_output(['proxy', url_string])
    except subprocess.CalledProcessError as e:
        log.network.exception("Failed to call proxy subprocess: {}".format(e))
        return []

    try:
        proxy_urls = proxy_urls.decode('utf-8').strip().split()
    except UnicodeDecodeError as e:
        log.network.exception("Failed to decode proxies: {}".format(e))
        return []

    log.network.debug("Proxy URLs: {!r}".format(proxy_urls))
    if not proxy_urls:
        return []

    proxies = []
    for proxy_url in proxy_urls:
        try:
            proxies.append(urlutils.proxy_from_url(QUrl(proxy_url)))
        except (urlutils.InvalidUrlError, urlutils.InvalidProxyTypeError) as e:
            log.network.error("Failed to parse proxy URL {}".format(proxy_url))

    return proxies


def _system_proxy(query):
    proxies = _system_proxy_subprocess(query.url())
    if not proxies:
        raise Exception
        proxies = QNetworkProxyFactory.systemProxyForQuery(query)
    return proxies


class ProxyFactory(QNetworkProxyFactory):

    """Factory for proxies to be used by qutebrowser."""

    def get_error(self):
        """Check if proxy can't be resolved.

        Return:
           None if proxy is correct, otherwise an error message.
        """
        proxy = config.get('network', 'proxy')
        if isinstance(proxy, pac.PACFetcher):
            return proxy.fetch_error()
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
            proxies = _system_proxy(query)
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
