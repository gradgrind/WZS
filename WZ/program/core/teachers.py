"""
core/teachers.py - last updated 2023-11-18

Manage teacher data.

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

import sys, os

if __name__ == "__main__":
    # Enable package import if running as module
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

#from core.base import TRANSLATIONS
#T = TRANSLATIONS("core.teachers")

### +++++

from core.db_access import (
    DB_TABLES,
    db_Table,
    DB_PK,
    DB_FIELD_TEXT,
)

### -----


class Teachers(db_Table):
    table = "TEACHERS"
    order = "SORTNAME"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("TID", unique = True),
                DB_FIELD_TEXT("FIRSTNAMES"),
                DB_FIELD_TEXT("LASTNAME"),
                DB_FIELD_TEXT("SIGNED", unique = True),
                DB_FIELD_TEXT("SORTNAME", unique = True),
            )
            return True
        return False

#    def __init__(self, db: Database):
#        self.init()
#        super().__init__(db)

    @staticmethod
    def get_name(data):
        return f"{data.FIRSTNAMES} {data.LASTNAME}"

    def name(self, t_id):
        return self.get_name(self[t_id])

    def teacher_list(self, skip_null: bool = True):
        """Return an ordered list of teachers.
        """
        teachers = []
        for data in self.records:
            t = data.id
            if t != 0 or not skip_null:
                teachers.append((t, data.TID, self.get_name(data)))
        return teachers

    def tid_map(self) -> dict:
        """Return the data for all teachers as a mapping with the TID value
        as key.
        This data is cached, so subsequent calls get the same instance.
        """
        try:
            if self.__tid_map:
                return self.__tid_map
        except AttributeError:
            pass
        self.__tid_map = {
            data.TID: data
            for data in self.records
            if data.id
        }
        return self.__tid_map


DB_TABLES[Teachers.table] = Teachers


#TODO: Handle TT_TEACHERS table

# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.db_access import get_database
    db = get_database()

    #print("?sql:", Teachers.sql_create_table())

    teachers = Teachers(db)
    for t, index in teachers.id2index.items():
        print(
            f"\n  {t}: {teachers.name(t)}\n     ->"
            f" {index:02d}/{teachers.records[index]}"
        )

    print("\n**************************************\n teacher_list():")
    for data in teachers.teacher_list():
        print("  --", data)

    print("\n*************************************\n tid_map():")
    for tid, tdata in teachers.tid_map().items():
        print(f"\n  {tid}: {tdata}")
