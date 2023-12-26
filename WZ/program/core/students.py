"""
core/students.py - last updated 2023-12-26

Manage students data.


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

#from core.base import Tr
#T = Tr("core.students")

### +++++

from core.db_access import (
    DB_TABLES,
    db_Table,
    DB_PK,
    DB_FIELD_TEXT,
    DB_FIELD_REFERENCE,
)
from core.classes import Classes

### -----


class Students(db_Table):
    table = "STUDENTS"
    order = "SORTNAME"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_REFERENCE("Class", target = Classes.table),
                DB_FIELD_TEXT("PID", unique = True),
                DB_FIELD_TEXT("SORTNAME", unique = True),
                DB_FIELD_TEXT("EXTRA"),
            )
            return True
        return False

#    def __init__(self, db: Database):
#        self.init()
#        super().__init__(db)

    def student_list(self, class_id: int):
        """Return an ordered list of subjects from the given class.
        """
        students = []
        for data in self.records:
            if data.Class.id == class_id:
                students.append(data)
                print("  --", data)
#TODO: Process columns (e.g. EXTRA from json)
        return students


DB_TABLES[Students.table] = Students


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    db = get_database()

    #print("\n?create-sql:", Subjects.sql_create_table())

    students = Students(db)
    students.student_list(21)
#    for s, index in subjects.id2index.items():
#        print(f"\n  {s}: {index:02d}/{subjects.records[index]}")

#    print("\n**************************************\n subject_list():")
#    for s in subjects.subject_list():
#        print("  --", s)
