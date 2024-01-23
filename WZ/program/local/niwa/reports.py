"""
local/niwa/grades.py

Last updated:  2024-01-23

Regional support for report handling:
    Waldorfschule in Niedersachsen


=+LICENCE=============================
Copyright 2024 Michael Towers

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

=-LICENCE========================================
"""

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import Tr
T = Tr("local.reports")

### +++++

from core.base import REPORT_ERROR

FIELD_MAPPING = {
    "LEVEL": {"HS": "Hauptschule", "RS": "Realschule", "Gym": "Gymnasium"},
    "SEX": {"m": "Herr", "w": "Frau"},
    "OCCASION": {
        "2. Halbjahr": "1. und 2. Halbjahr",
        "$": "",
    }
}

### -----

def local_fields(fields: dict[str, str]):
    for f, v in fields.items():
        try:
            fmap = FIELD_MAPPING[f]
        except KeyError:
            continue
        try:
            fields[f] = fmap[v]
        except KeyError:
            try:
                vx = fmap["$"]
                if vx:
                    fields[f] = vx.replace("$", v)
            except KeyError:
                REPORT_ERROR(T("INVALID_VALUE",
                    key = f,
                    value = v,
                    valid = ", ".join(fmap),
                ))
    # Additional fields:
    fields["SCHOOLBIG"] = fields["SCHOOL"].upper()
    fields["-REMARKS"] = "––––––––––––"
