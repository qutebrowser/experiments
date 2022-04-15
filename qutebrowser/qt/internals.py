class AbstractInternals:

    def init_backend(self):
        raise NotImplementedError

    def is_deleted(self, obj):
        raise NotImplementedError

    def delete(self, obj):
        raise NotImplementedError

    def assign(self, target, value):
        raise NotImplementedError


class PyQtInternals(AbstractInternals):

    def init_backend(self):
        """Remove the PyQt input hook and enable overflow checking.

        Doing this means we can't use the interactive shell anymore (which we don't
        anyways), but we can use pdb instead.
        """
        self.qtcore.pyqtRemoveInputHook()

        try:
            self.qtcore.pyqt5_enable_new_onexit_scheme(True)  # type: ignore[attr-defined]
        except AttributeError:
            # Added in PyQt 5.13 somewhere, going to be the default in 5.14
            pass

        try:
            self.sip.enableoverflowchecking(True)
        except AttributeError:
            # default in PyQt6
            # FIXME:qt6 solve this in qutebrowser/qt/sip.py equivalent
            pass

    def is_deleted(self, obj):
        return self.sip.is_deleted(obj)

    def delete(self, obj):
        return self.sip.delete(obj)

    def assign(self, target, value):
        self.sip.assign(target, value)


class PySideInternals(AbstractInternals):

    def init_backend(self):
        pass

    def is_deleted(self, obj):
        return not self.shiboken.isValid(obj)

    def delete(self, obj):
        return self.shiboken.delete(obj)


class PyQt5Internals(PyQtInternals):

    def __init__(self):
        # While upstream recommends using PyQt6.sip ever since PyQt6 5.11, some
        # distributions still package later versions of PyQt6 with a top-level
        # "sip" rather than "PyQt6.sip".
        try:
            from PyQt5 import sip
        except ImportError:
            import sip
        from PyQt5 import QtCore

        self.sip = sip
        self.qtcore = QtCore
        self.object = sip.simplewrapper
        self.voidptr = sip.voidptr



class PyQt6Internals(PyQtInternals):

    def __init__(self):
        from PyQt6 import sip, QtCore
        self.sip = sip
        self.qtcore = QtCore
        self.object = sip.simplewrapper
        self.voidptr = sip.voidptr


class PySide2Internals(PySideInternals):

    def __init__(self):
        import shiboken2
        self.shiboken = shiboken2
        self.object = shiboken2.Object
        self.voidptr = shiboken2.VoidPtr


class PySide6Internals(PySideInternals):

    def __init__(self):
        import shiboken6
        self.shiboken = shiboken6
        self.object = shiboken6.Object
        self.voidptr = shiboken6.VoidPtr
