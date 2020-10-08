# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2015-2020 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
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

"""Various utilities used inside tests."""

from __future__ import generator_stop, annotations

import io
import re
import gzip
import pprint
import os.path
import contextlib
import pathlib
import importlib.util
import importlib.machinery

import pytest

from PyQt5.QtCore import qVersion
try:
    from PyQt5.QtWebEngine import PYQT_WEBENGINE_VERSION_STR
except ImportError:
    PYQT_WEBENGINE_VERSION_STR = None

from qutebrowser.utils import qtutils, log

ON_CI = 'CI' in os.environ

qt58 = pytest.mark.skipif(
    qtutils.version_check('5.9'), reason="Needs Qt 5.8 or earlier")
qt59 = pytest.mark.skipif(
    not qtutils.version_check('5.9'), reason="Needs Qt 5.9 or newer")
qt510 = pytest.mark.skipif(
    not qtutils.version_check('5.10'), reason="Needs Qt 5.10 or newer")
qt514 = pytest.mark.skipif(
    not qtutils.version_check('5.14'), reason="Needs Qt 5.14 or newer")
skip_qt511 = pytest.mark.skipif(
    qtutils.version_check('5.11'), reason="Needs Qt 5.10 or earlier")


class PartialCompareOutcome:

    """Storage for a partial_compare error.

    Evaluates to False if an error was found.

    Attributes:
        error: A string describing an error or None.
    """

    def __init__(self, error=None):
        self.error = error

    def __bool__(self):
        return self.error is None

    def __repr__(self):
        return 'PartialCompareOutcome(error={!r})'.format(self.error)

    def __str__(self):
        return 'true' if self.error is None else 'false'


def print_i(text, indent, error=False):
    if error:
        text = '| ****** {} ******'.format(text)
    for line in text.splitlines():
        print('|   ' * indent + line)


def _partial_compare_dict(val1, val2, *, indent):
    for key in val2:
        if key not in val1:
            outcome = PartialCompareOutcome(
                "Key {!r} is in second dict but not in first!".format(key))
            print_i(outcome.error, indent, error=True)
            return outcome
        outcome = partial_compare(val1[key], val2[key], indent=indent + 1)
        if not outcome:
            return outcome
    return PartialCompareOutcome()


def _partial_compare_list(val1, val2, *, indent):
    if len(val1) < len(val2):
        outcome = PartialCompareOutcome(
            "Second list is longer than first list")
        print_i(outcome.error, indent, error=True)
        return outcome
    for item1, item2 in zip(val1, val2):
        outcome = partial_compare(item1, item2, indent=indent + 1)
        if not outcome:
            return outcome
    return PartialCompareOutcome()


def _partial_compare_float(val1, val2, *, indent):
    if val1 == pytest.approx(val2):
        return PartialCompareOutcome()

    return PartialCompareOutcome("{!r} != {!r} (float comparison)".format(
        val1, val2))


def _partial_compare_str(val1, val2, *, indent):
    if pattern_match(pattern=val2, value=val1):
        return PartialCompareOutcome()

    return PartialCompareOutcome("{!r} != {!r} (pattern matching)".format(
        val1, val2))


def _partial_compare_eq(val1, val2, *, indent):
    if val1 == val2:
        return PartialCompareOutcome()
    return PartialCompareOutcome("{!r} != {!r}".format(val1, val2))


def gha_group_begin(name):
    """Get a string to begin a GitHub Actions group.

    Should only be called on CI.
    """
    assert ON_CI
    return '::group::' + name


def gha_group_end():
    """Get a string to end a GitHub Actions group.

    Should only be called on CI.
    """
    assert ON_CI
    return '::endgroup::'


def partial_compare(val1, val2, *, indent=0):
    """Do a partial comparison between the given values.

    For dicts, keys in val2 are checked, others are ignored.
    For lists, entries at the positions in val2 are checked, others ignored.
    For other values, == is used.

    This happens recursively.
    """
    if ON_CI and indent == 0:
        print(gha_group_begin('Comparison'))

    print_i("Comparing", indent)
    print_i(pprint.pformat(val1), indent + 1)
    print_i("|---- to ----", indent)
    print_i(pprint.pformat(val2), indent + 1)

    if val2 is Ellipsis:
        print_i("Ignoring ellipsis comparison", indent, error=True)
        return PartialCompareOutcome()
    elif type(val1) != type(val2):  # pylint: disable=unidiomatic-typecheck
        outcome = PartialCompareOutcome(
            "Different types ({}, {}) -> False".format(type(val1).__name__,
                                                       type(val2).__name__))
        print_i(outcome.error, indent, error=True)
        return outcome

    handlers = {
        dict: _partial_compare_dict,
        list: _partial_compare_list,
        float: _partial_compare_float,
        str: _partial_compare_str,
    }

    for typ, handler in handlers.items():
        if isinstance(val2, typ):
            print_i("|======= Comparing as {}".format(typ.__name__), indent)
            outcome = handler(val1, val2, indent=indent)
            break
    else:
        print_i("|======= Comparing via ==", indent)
        outcome = _partial_compare_eq(val1, val2, indent=indent)
    print_i("---> {}".format(outcome), indent)

    if ON_CI and indent == 0:
        print(gha_group_end())

    return outcome


def pattern_match(*, pattern, value):
    """Do fnmatch.fnmatchcase like matching, but only with * active.

    Return:
        True on a match, False otherwise.
    """
    re_pattern = '.*'.join(re.escape(part) for part in pattern.split('*'))
    return re.fullmatch(re_pattern, value, flags=re.DOTALL) is not None


def abs_datapath():
    """Get the absolute path to the end2end data directory."""
    file_abs = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(file_abs, '..', 'end2end', 'data')


@contextlib.contextmanager
def nop_contextmanager():
    yield


@contextlib.contextmanager
def change_cwd(path):
    """Use a path as current working directory."""
    old_cwd = pathlib.Path.cwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(str(old_cwd))


@contextlib.contextmanager
def ignore_bs4_warning():
    """WORKAROUND for https://bugs.launchpad.net/beautifulsoup/+bug/1847592."""
    with log.ignore_py_warnings(
            category=DeprecationWarning,
            message="Using or importing the ABCs from 'collections' instead "
            "of from 'collections.abc' is deprecated", module='bs4.element'):
        yield


def blocked_hosts():
    path = os.path.join(abs_datapath(), 'blocked-hosts.gz')
    yield from io.TextIOWrapper(gzip.open(path), encoding='utf-8')


def seccomp_args(qt_flag):
    """Get necessary flags to disable the seccomp BPF sandbox.

    This is needed for some QtWebEngine setups, with older Qt versions but
    newer kernels.

    Args:
        qt_flag: Add a '--qt-flag' argument.
    """
    affected_versions = set()
    for base, patch_range in [
            ## seccomp-bpf failure in syscall 0281
            ## https://github.com/qutebrowser/qutebrowser/issues/3163
            # 5.7.1
            ('5.7', [1]),

            ## seccomp-bpf failure in syscall 0281 (clock_nanosleep)
            ## https://bugreports.qt.io/browse/QTBUG-81313
            # 5.11.0 to 5.11.3 (inclusive)
            ('5.11', range(0, 4)),
            # 5.12.0 to 5.12.7 (inclusive)
            ('5.12', range(0, 8)),
            # 5.13.0 to 5.13.2 (inclusive)
            ('5.13', range(0, 3)),
            # 5.14.0
            ('5.14', [0]),
    ]:
        for patch in patch_range:
            affected_versions.add('{}.{}'.format(base, patch))

    version = (PYQT_WEBENGINE_VERSION_STR
               if PYQT_WEBENGINE_VERSION_STR is not None
               else qVersion())
    if version in affected_versions:
        disable_arg = 'disable-seccomp-filter-sandbox'
        return ['--qt-flag', disable_arg] if qt_flag else ['--' + disable_arg]

    return []


def import_userscript(name):
    """Import a userscript via importlib.

    This is needed because userscripts don't have a .py extension and violate
    Python's module naming convention.
    """
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    script_path = repo_root / 'misc' / 'userscripts' / name
    module_name = name.replace('-', '_')
    loader = importlib.machinery.SourceFileLoader(
        module_name, str(script_path))
    spec = importlib.util.spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
