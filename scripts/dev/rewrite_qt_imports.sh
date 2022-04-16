#!/bin/bash

fd -g '*.py' -E 'qt' qutebrowser/ tests/ | xargs sed -i \
    -e 's/from PyQt6 import QtCore/from qutebrowser.qt import core as QtCore/' \
    -e 's/from PyQt6 import QtWebEngine/from qutebrowser.qt import webengine as QtWebEngine/' \
    -e 's/from PyQt6 import QtWebEngineWidgets/from qutebrowser.qt import webenginewidgets as QtWebEngineWidgets/' \
    -e 's/from PyQt6 import QtWebKit/from qutebrowser.qt import webkit as QtWebKit/' \
    -e 's/from PyQt6 import QtWebKitWidgets/from qutebrowser.qt import webkitwidgets as QtWebKitWidgets/' \
    -e 's/from PyQt6.QtCore/from qutebrowser.qt.core/' \
    -e 's/from PyQt6.QtGui/from qutebrowser.qt.gui/' \
    -e 's/from PyQt6.QtNetwork/from qutebrowser.qt.network/' \
    -e 's/from PyQt6.QtWebEngineCore/from qutebrowser.qt.webenginecore/' \
    -e 's/from PyQt6.QtWebEngineWidgets/from qutebrowser.qt.webenginewidgets/' \
    -e 's/from PyQt6.QtWebEngine/from qutebrowser.qt.webengine/' \
    -e 's/from PyQt6.QtWebKitWidgets/from qutebrowser.qt.webkitwidgets/' \
    -e 's/from PyQt6.QtWebKit/from qutebrowser.qt.webkit/' \
    -e 's/from PyQt6.QtWidgets/from qutebrowser.qt.widgets/' \
    -e 's/from PyQt6.QtPrintSupport/from qutebrowser.qt.printsupport/' \
    -e 's/from PyQt6.QtQml/from qutebrowser.qt.qml/' \
    -e 's/from PyQt6.QtSql/from qutebrowser.qt.sql/' \
    -e 's/from PyQt6.QtTest/from qutebrowser.qt.test/' \
    -e 's/from PyQt6.QtDBus/from qutebrowser.qt.dbus/'
