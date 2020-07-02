#!/usr/bin/env python3
# vim: ft=sh fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2020 Florian Bruhin (The Compiler) <mail@qutebrowser.org>

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

"""Register problem matchers for GitHub Actions.

Relevant docs:
https://github.com/actions/toolkit/blob/master/docs/problem-matchers.md
https://github.com/actions/toolkit/blob/master/docs/commands.md#problem-matchers
"""

import sys
import tempfile
import pathlib
import json


MATCHERS = {
    # scripts/dev/ci/run.sh:41:39: error: Double quote array expansions to
    # avoid re-splitting elements. [SC2068]
    "shellcheck": {
        "pattern": [
            {
                "regexp": r"^(.+):(\d+):(\d+):\s(note|warning|error):\s(.*)\s\[(SC\d+)\]$",
                "file": 1,
                "line": 2,
                "column": 3,
                "severity": 4,
                "message": 5,
                "code": 6,
            },
        ],
    },

    # filename.py:313: unused function 'i_am_never_used' (60% confidence)
    "vulture": {
        "severity": "warning",
        "pattern": [
            {
                "regexp": r"^([^:]+):(\d+): ([^(]+ \(\d+% confidence\))$",
                "file": 1,
                "line": 2,
                "message": 3,
            }
        ]
    },

    # filename.py:1:1: D100 Missing docstring in public module
    "flake8": {
        # "undefined name" is FXXX (i.e. not an error), but e.g. multiple
        # spaces before an operator is EXXX (i.e. an error) - that makes little
        # sense, so let's just treat everything as a warning instead.
        "pattern-warning": [
            {
                "regexp": r"^([^:]+):(\d+):(\d+): ([A-Z]\d{3}) (.*)$",
                "file": 1,
                "line": 2,
                "column": 3,
                "code": 4,
                "message": 5,
            },
        ],
    },

    # filename.py:80: error: Name 'foo' is not defined  [name-defined]
    "mypy": {
        "pattern": [
            {
                "regexp": r"^([^:]+):(\d+): ([^:]+): (.*)  \[(.*)\]$",
                "file": 1,
                "line": 2,
                "severity": 3,
                "message": 4,
                "code": 5,
            },
        ],
    },

    "pylint": {
        # filename.py:80:10: E0602: Undefined variable 'foo' (undefined-variable)
        "pattern-error": [
            {
                "regexp": r"^([^:]+):(\d+):(\d+): (E\d+): (.*)",
                "file": 1,
                "line": 2,
                "column": 3,
                "code": 4,
                "message": 5,
            },
        ],

        # filename.py:78:14: W0613: Unused argument 'unused' (unused-argument)
        "pattern-warning": [
            {
                "regexp": r"^([^:]+):(\d+):(\d+): ([A-DF-Z]\d+): (.*)",
                "file": 1,
                "line": 2,
                "column": 3,
                "code": 4,
                "message": 5,
            },
        ],
    },
}


def add_matcher(output_dir, testenv, pattern, severity=None):
    owner = (testenv if severity is None
             else '{}-{}'.format(testenv, severity))

    output = {
        'owner': owner,
        'pattern': pattern,
    }
    if severity is not None:
        output['severity'] = severity

    data = {'problemMatcher': [output]}

    output_file = output_dir / '{}.json'.format(owner)
    with output_file.open('w', encoding='utf-8') as f:
        json.dump(data, f)

    print("::add-matcher::{}".format(output_file))


def main():
    testenv = sys.argv[1]
    if testenv not in MATCHERS:
        return 0

    # We're not deleting the temporary file because this is only running on CI
    # anyways, and we're not sure if GitHub has already read the file contents
    # at the point this script exits.
    output_dir = pathlib.Path(tempfile.mkdtemp(suffix='-ghmatchers'))

    matcher_data = MATCHERS[testenv]

    for key, severity in [('pattern', None),
                          ('pattern-warning', 'warning'),
                          ('pattern-error', 'error')]:
        if key in matcher_data:
            add_matcher(output_dir=output_dir,
                        testenv=testenv,
                        pattern=matcher_data[key],
                        severity=severity)


if __name__ == '__main__':
    sys.exit(main())
