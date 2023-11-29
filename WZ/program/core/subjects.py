"""
core/subjects.py - last updated 2023-11-18

Manage subjects data.

=+LICENCE=================================
Copyright 2023 Michael Towers

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
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

#from core.base import TRANSLATIONS
#T = TRANSLATIONS("core.subjects")

### +++++

from core.db_access import (
    DB_TABLES,
    db_Table,
    DB_PK,
    DB_FIELD_TEXT,
)

### -----


class Subjects(db_Table):
    table = "SUBJECTS"
    order = "NAME"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("SID", unique = True),
                DB_FIELD_TEXT("NAME", unique = True),
                DB_FIELD_TEXT("SORTING"),
            )
            return True
        return False

#    def __init__(self, db: Database):
#        self.init()
#        super().__init__(db)

    def subject_list(self, skip_null: bool = True):
        """Return an ordered list of subjects.
        """
        subjects = []
        for data in self.records:
            s = data.id
            if s != 0 or not skip_null:
                subjects.append((s, data.SID, data.NAME))
        return subjects


DB_TABLES[Subjects.table] = Subjects


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.db_access import get_database
    db = get_database()

    #print("\n?create-sql:", Subjects.sql_create_table())

    subjects = Subjects(db)
    for s, index in subjects.id2index.items():
        print(f"\n  {s}: {index:02d}/{subjects.records[index]}")

    print("\n**************************************\n subject_list():")
    for s in subjects.subject_list():
        print("  --", s)
