from qutebrowser.qt import machinery


if machinery.USE_PYQT5:
    from PyQt5.QtCore import *
elif machinery.USE_PYQT6:
    from PyQt6.QtCore import *
elif machinery.USE_PYSIDE2:
    from PySide2.QtCore import *
elif machinery.USE_PYSIDE6:
    from PySide6.QtCore import *
else:
    raise machinery.UnknownWrapper()


if machinery.IS_PYQT:
    Signal = pyqtSignal
    Slot = pyqtSlot
    SignalInstance = pyqtBoundSignal
    del pyqtSignal
    del pyqtSlot
    del pyqtBoundSignal
else:
    QVariant = None  # FIXME:qt6 what to do about this?
