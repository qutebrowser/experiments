import os
import importlib
import dataclasses
import types


_WRAPPERS = ["PyQt6", "PyQt5", "PySide6", "PySide2"]


class Error(Exception):
    pass


class Unavailable(Error, ImportError):
    pass


class UnknownWrapper(Error):
    pass


@dataclasses.dataclass
class QtVersionInfo:

    # FIXME:qt6 provide parsed versions here?
    # FIXME:qt6 what about qVersion()?

    qt: str
    qt_hex: int
    wrapper: str
    wrapper_hex: int

    @classmethod
    def from_pyside(
        cls,
        qtcore_mod: types.ModuleType,
        pyside_mod: types.ModuleType,
    ) -> 'QtVersionInfo':
        qt_major, qt_minor, qt_patch = qtcore_mod.__version_info__
        (
            wrapper_major,
            wrapper_minor,
            wrapper_patch,
            _suffix1,
            _suffix2
        ) = pyside_mod.__version_info__
        qt_hex = qt_major << 16 | qt_minor << 8 | qt_patch
        wrapper_hex = wrapper_major << 16 | wrapper_minor << 8 | wrapper_patch
        return cls(
            qt=qtcore_mod.__version__,
            qt_hex=qt_hex,
            wrapper=pyside_mod.__version__,
            wrapper_hex=wrapper_hex,
        )

    @classmethod
    def from_pyqt(cls, qtcore_mod: types.ModuleType) -> 'QtVersionInfo':
        return cls(
            qt=qtcore_mod.QT_VERSION_STR,
            qt_hex=qtcore_mod.QT_VERSION,
            wrapper=qtcore_mod.PYQT_VERSION_STR,
            wrapper_hex=qtcore_mod.PYQT_VERSION,
        )


def _autoselect_wrapper():
    for wrapper in _WRAPPERS:
        try:
            importlib.import_module(wrapper)
        except ImportError:
            # FIXME:qt6 show/log this somewhere?
            continue

        # FIXME:qt6 what to do if none are available?
        return wrapper


def _select_wrapper():
    env_var = "QUTE_QT_WRAPPER"
    env_wrapper = os.environ.get(env_var)
    if env_wrapper is None:
        return _autoselect_wrapper()

    if env_wrapper not in _WRAPPERS:
        raise Error(f"Unknown wrapper {env_wrapper} set via {env_var}, "
                    f"allowed: {', '.join(_WRAPPERS)}")

    return env_wrapper


WRAPPER = _select_wrapper()
USE_PYQT5 = WRAPPER == "PyQt5"
USE_PYQT6 = WRAPPER == "PyQt6"
USE_PYSIDE2 = WRAPPER == "PySide2"
USE_PYSIDE6 = WRAPPER == "PySide6"
assert USE_PYQT5 ^ USE_PYQT6 ^ USE_PYSIDE2 ^ USE_PYSIDE6

IS_QT5 = USE_PYQT5 or USE_PYSIDE2
IS_QT6 = USE_PYQT6 or USE_PYSIDE6
IS_PYQT = USE_PYQT5 or USE_PYQT6
IS_PYSIDE = USE_PYSIDE2 or USE_PYSIDE6
assert IS_QT5 ^ IS_QT6
assert IS_PYQT ^ IS_PYSIDE


if USE_PYQT5:
    PACKAGE = "PyQt5"
    from PyQt5 import QtCore as _QtCore
    VERSIONS = QtVersionInfo.from_pyqt(_QtCore)
elif USE_PYQT6:
    PACKAGE = "PyQt6"
    from PyQt6 import QtCore as _QtCore
    VERSIONS = QtVersionInfo.from_pyqt(_QtCore)
elif USE_PYSIDE2:
    PACKAGE = "PySide2"
    from PySide2 import QtCore as _QtCore
    import PySide2 as _PySide2
    VERSIONS = QtVersionInfo.from_pyside(qtcore_mod=_QtCore, pyside_mod=_PySide2)
elif USE_PYSIDE6:
    PACKAGE = "PySide6"
    from PySide6 import QtCore as _QtCore
    import PySide6 as _PySide6
    VERSIONS = QtVersionInfo.from_pyside(qtcore_mod=_QtCore, pyside_mod=_PySide6)
