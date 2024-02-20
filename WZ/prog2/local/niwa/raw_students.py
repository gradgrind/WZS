"""
local/niwa/raw_students.py

Last updated:  2024-02-20

Importiere Schülerdaten

=+LICENCE=================================
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

=-LICENCE=================================
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
T = Tr("local.raw_students")

### +++++

from typing import Optional

from core.base import REPORT_ERROR
from tables.ods_support import ODS_reader
from local.tussenvoegsel import tussenvoegsel_filter

### -----


#TODO -> config
HEADERS = (
    ("CLASS", "Schulklasse"),   # -> "Class_id"
    ("PID", "ID"),
    ("SORTNAME", ""),
    ("LASTNAME", "Name"),
    ("FIRSTNAMES", "Vornamen"),
    ("FIRSTNAME", "Rufname"),
    ("DATE_BIRTH", "Geburtsdatum"),
    ("DATE_ENTRY", "Eintrittsdatum"),
    ("DATE_EXIT", "Austrittsdatum"),
    ("BIRTHPLACE", "Geburtsort"),
    ("GROUPS", ""),

    # Additional, non-core headers
    ("HOME", "Ort"),
    ("SEX", "Geschlecht"),
)


def read_raw_students_data(
    filepath: str,
    classmap: dict[str, int]
) -> Optional[list[dict[str, str | int]]]:
    rows = ODS_reader(filepath)
    tmap = {t.lower(): c for c, t in enumerate(rows[0])}
    clist = []
    for h, t in HEADERS:
        if t:
            try:
                clist.append((h, tmap[t.lower()]))
            except KeyError:
                REPORT_ERROR(T("MISSING_FIELD_IN_TABLE", field = t))
                return None
        else:
            clist.append((h, -1))
    records = []
    for r in range(1, len(rows)):
        row = rows[r]
        #print(f"{i:03d}:", row)
        rec = {h: row[c] if c >= 0 else "" for h, c in clist}
        if not rec["PID"]:
            continue    # skip line, assume not relevant
        rec["Class_id"] = classmap[rec.pop("CLASS")]
        (
            rec["FIRSTNAMES"],
            rec["LASTNAME"],
            rec["FIRSTNAME"],
            rec["SORTNAME"]
        ) = tussenvoegsel_filter(
            rec["FIRSTNAMES"], rec["LASTNAME"], rec["FIRSTNAME"]
        )
        records.append(rec)
    return records


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import DATAPATH
    from core.classes import get_database, Classes

    classes = Classes(get_database())
    classmap = {
        rec.CLASS: rec.id
        for rec in classes.records
        if rec.id > 0
    }
    fpath = DATAPATH("test_students_data.ods", "working_data")
    records = read_raw_students_data(fpath, classmap)
    for rec in records:
        print(" --", rec)
