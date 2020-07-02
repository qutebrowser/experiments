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

import sys
import tempfile
import pathlib
import json

MATCHERS = {
    "shellcheck": [
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
}


def main():
    testenv = sys.argv[1]
    if testenv not in MATCHERS:
        return 0

    output_dir = pathlib.Path(tempfile.mkdtemp(suffix='-ghmatchers'))

    data = {
        'problemMatcher': [
            {
                'owner': testenv,
                'pattern': MATCHERS[testenv],
            },
        ],
    }

    output_file = output_dir / '{}.json'.format(testenv)
    with output_file.open('w', encoding='utf-8') as f:
        json.dump(data, f)

    print("::add-matcher::{}".format(output_file))


if __name__ == '__main__':
    sys.exit(main())
