# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014-2021 Florian Bruhin (The-Compiler) <mail@qutebrowser.org>
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
# along with qutebrowser.  If not, see <https://www.gnu.org/licenses/>.

"""Things which need to be done really early (e.g. before importing Qt).

At this point we can be sure we have all python 3.7 features available.
"""

try:
    # Importing hunter to register its atexit handler early so it gets called
    # late.
    import hunter  # pylint: disable=unused-import
except ImportError:
    hunter = None

import sys
import faulthandler
import traceback
import signal
import importlib
import datetime
try:
    import tkinter
except ImportError:
    tkinter = None  # type: ignore[assignment]

# NOTE: No qutebrowser or PyQt import should be done here, as some early
# initialization needs to take place before that!


START_TIME = datetime.datetime.now()


def _missing_str(name, *, webengine=False):
    """Get an error string for missing packages.

    Args:
        name: The name of the package.
        webengine: Whether this is checking the QtWebEngine package
    """
    blocks = ["Fatal error: <b>{}</b> is required to run qutebrowser but "
              "could not be imported! Maybe it's not installed?".format(name),
              "<b>The error encountered was:</b><br />%ERROR%"]
    lines = ['Please search for the python3 version of {} in your '
             'distributions packages, or see '
             'https://github.com/qutebrowser/qutebrowser/blob/master/doc/install.asciidoc'
             .format(name)]
    blocks.append('<br />'.join(lines))
    if not webengine:
        lines = ['<b>If you installed a qutebrowser package for your '
                 'distribution, please report this as a bug.</b>']
        blocks.append('<br />'.join(lines))
    return '<br /><br />'.join(blocks)


def _die(message, exception=None):
    """Display an error message using Qt and quit.

    We import the imports here as we want to do other stuff before the imports.

    Args:
        message: The message to display.
        exception: The exception object if we're handling an exception.
    """
    from qutebrowser.qt.widgets import QApplication, QMessageBox
    from qutebrowser.qt.core import Qt
    if (('--debug' in sys.argv or '--no-err-windows' in sys.argv) and
            exception is not None):
        print(file=sys.stderr)
        traceback.print_exc()
    app = QApplication(sys.argv)
    if '--no-err-windows' in sys.argv:
        print(message, file=sys.stderr)
        print("Exiting because of --no-err-windows.", file=sys.stderr)
    else:
        if exception is not None:
            message = message.replace('%ERROR%', str(exception))
        msgbox = QMessageBox(QMessageBox.Icon.Critical, "qutebrowser: Fatal error!",
                             message)
        msgbox.setTextFormat(Qt.TextFormat.RichText)
        msgbox.resize(msgbox.sizeHint())
        msgbox.exec()
    app.quit()
    sys.exit(1)


def init_faulthandler(fileobj=sys.__stderr__):
    """Enable faulthandler module if available.

    This print a nice traceback on segfaults.

    We use sys.__stderr__ instead of sys.stderr here so this will still work
    when sys.stderr got replaced, e.g. by "Python Tools for Visual Studio".

    Args:
        fileobj: An opened file object to write the traceback to.
    """
    try:
        faulthandler.enable(fileobj)
    except (RuntimeError, AttributeError):
        # When run with pythonw.exe, sys.__stderr__ can be None:
        # https://docs.python.org/3/library/sys.html#sys.__stderr__
        #
        # With PyInstaller, it can be a NullWriter raising AttributeError on
        # fileno: https://github.com/pyinstaller/pyinstaller/issues/4481
        #
        # Later when we have our data dir available we re-enable faulthandler
        # to write to a file so we can display a crash to the user at the next
        # start.
        #
        # Note that we don't have any logging initialized yet at this point, so
        # this is a silent error.
        return

    if (hasattr(faulthandler, 'register') and hasattr(signal, 'SIGUSR1') and
            sys.stderr is not None):
        # If available, we also want a traceback on SIGUSR1.
        # pylint: disable=no-member,useless-suppression
        faulthandler.register(signal.SIGUSR1)
        # pylint: enable=no-member,useless-suppression


def check_pyqt():
    """Check if PyQt core modules (QtCore/QtWidgets) are installed."""
    from qutebrowser.qt import machinery

    packages = [f'{machinery.PACKAGE}.QtCore', f'{machinery.PACKAGE}.QtWidgets']
    for name in packages:
        try:
            importlib.import_module(name)
        except ImportError as e:
            text = _missing_str(name)
            text = text.replace('<b>', '')
            text = text.replace('</b>', '')
            text = text.replace('<br />', '\n')
            text = text.replace('%ERROR%', str(e))
            if tkinter and '--no-err-windows' not in sys.argv:
                root = tkinter.Tk()
                root.withdraw()
                tkinter.messagebox.showerror("qutebrowser: Fatal error!", text)
            else:
                print(text, file=sys.stderr)
            if '--debug' in sys.argv or '--no-err-windows' in sys.argv:
                print(file=sys.stderr)
                traceback.print_exc()
            sys.exit(1)


def qt_version(qversion=None, qt_version_str=None):
    """Get a Qt version string based on the runtime/compiled versions."""
    if qversion is None:
        from qutebrowser.qt.core import qVersion
        qversion = qVersion()
    if qt_version_str is None:
        from qutebrowser.qt.machinery import VERSIONS
        qt_version_str = VERSIONS.qt

    if qversion != qt_version_str:
        return '{} (compiled {})'.format(qversion, qt_version_str)
    else:
        return qversion


def check_qt_version():
    """Check if the Qt version is recent enough."""
    from qutebrowser.qt import machinery
    try:
        from qutebrowser.qt.core import QVersionNumber, QLibraryInfo
        qt_ver = QLibraryInfo.version().normalized()
        recent_qt_runtime = qt_ver >= QVersionNumber(5, 12)  # type: ignore[operator]
    except (ImportError, AttributeError):
        # QVersionNumber was added in Qt 5.6, QLibraryInfo.version() in 5.8
        recent_qt_runtime = False

    if machinery.VERSIONS.qt_hex < 0x050C00 or machinery.VERSIONS.wrapper_hex < 0x050C00 or not recent_qt_runtime:
        text = (
            f"Fatal error: Qt >= 5.12.0 and {machinery.PACKAGE} >= 5.12.0 are "
            f"required, but Qt {qt_version()} / {machinery.PACKAGE} "
            f"{machinery.VERSIONS.wrapper} is installed.")
        _die(text)

    if qt_ver == QVersionNumber(5, 12, 0):
        from qutebrowser.utils import log
        log.init.warning("Running on Qt 5.12.0. Doing so is unsupported "
                         "(newer 5.12.x versions are fine).")


def check_ssl_support():
    """Check if SSL support is available."""
    try:
        from qutebrowser.qt.network import QSslSocket  # pylint: disable=unused-import
    except ImportError:
        _die("Fatal error: Your Qt is built without SSL support.")


def _check_modules(modules):
    """Make sure the given modules are available."""
    from qutebrowser.utils import log

    for name, text in modules.items():
        try:
            with log.py_warning_filter(
                category=DeprecationWarning,
                message=r'invalid escape sequence'
            ), log.py_warning_filter(
                category=ImportWarning,
                message=r'Not importing directory .*: missing __init__'
            ), log.py_warning_filter(
                category=DeprecationWarning,
                message=r'the imp module is deprecated',
            ), log.py_warning_filter(
                # WORKAROUND for https://github.com/pypa/setuptools/issues/2466
                category=DeprecationWarning,
                message=r'Creating a LegacyVersion has been deprecated',
            ):
                importlib.import_module(name)
        except ImportError as e:
            _die(text, e)


def check_libraries():
    """Check if all needed Python libraries are installed."""
    from qutebrowser.qt import machinery
    modules = {
        'jinja2': _missing_str("jinja2"),
        'yaml': _missing_str("PyYAML"),
    }
    for subpkg in ['QtQml', 'QtOpenGL', 'QtDBus']:
        package = f'{machinery.PACKAGE}.{subpkg}'
        modules[package] = _missing_str(package)
    if sys.version_info < (3, 9):
        # Backport required
        modules['importlib_resources'] = _missing_str("importlib_resources")
    _check_modules(modules)


def init_backend():
    from qutebrowser.qt import machinery
    machinery.INTERNALS.init_backend()


def init_log(args):
    """Initialize logging.

    Args:
        args: The argparse namespace.
    """
    from qutebrowser.utils import log
    log.init_log(args)
    log.init.debug("Log initialized.")


def check_optimize_flag():
    """Check whether qutebrowser is running with -OO."""
    from qutebrowser.utils import log
    if sys.flags.optimize >= 2:
        log.init.warning("Running on optimize level higher than 1, "
                         "unexpected behavior may occur.")


def webengine_early_import():
    """If QtWebEngine is available, import it early.

    We need to ensure that QtWebEngine is imported before a QApplication is created for
    everything to work properly.

    This needs to be done even when using the QtWebKit backend, to ensure that e.g.
    error messages in backendproblem.py are accurate.
    """
    try:
        from qutebrowser.qt import webenginewidgets  # pylint: disable=unused-import
    except ImportError:
        pass


def early_init(args):
    """Do all needed early initialization.

    Note that it's vital the other earlyinit functions get called in the right
    order!

    Args:
        args: The argparse namespace.
    """
    # First we initialize the faulthandler as early as possible, so we
    # theoretically could catch segfaults occurring later during earlyinit.
    init_faulthandler()
    # Here we check if QtCore is available, and if not, print a message to the
    # console or via Tk.
    check_pyqt()
    # Init logging as early as possible
    init_log(args)
    # Now we can be sure QtCore is available, so we can print dialogs on
    # errors, so people only using the GUI notice them as well.
    check_libraries()
    check_qt_version()
    init_backend()
    check_ssl_support()
    check_optimize_flag()
    webengine_early_import()
