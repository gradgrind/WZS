"""
core/students.py - last updated 2023-12-27

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
    DB_FIELD_JSON,
    DB_FIELD_REFERENCE,
)
from core.classes import Classes

EXTRA_SCHEMA = {
    "type": "object",
    "patternProperties":
        { "^[A-Za-z_][A-Za-z0-9_]*$": {"type": "string"}},
    #"additionalProperties": {"type": "string"},
    "additionalProperties": False
}

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
                DB_FIELD_TEXT("LASTNAME"),
                DB_FIELD_TEXT("FIRSTNAMES"),
                DB_FIELD_TEXT("FIRSTNAME"),
                DB_FIELD_TEXT("DATE_BIRTH"),
                DB_FIELD_TEXT("DATE_ENTRY"),
                DB_FIELD_TEXT("DATE_EXIT"),
                DB_FIELD_TEXT("BIRTHPLACE"),
                DB_FIELD_JSON("EXTRA", schema = EXTRA_SCHEMA)
            )
            return True
        return False

#    def __init__(self, db: Database):
#        self.init()
#        super().__init__(db)

    @staticmethod
    def get_name(data):
        """Return the short form of the name from the given record.
        """
        return f"{data.FIRSTNAME} {data.LASTNAME}"

    def name(self, id):
        """Return the short form of the name from the given db-id.
        """
        return self.get_name(self[id])

    def student_list(self, class_id: int):
        """Return an ordered list of subjects from the given class.
        """
        return [
            data
            for data in self.records
            if data.Class.id == class_id
        ]
#+
DB_TABLES[Students.table] = Students


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    db = get_database()

    #print("\n?create-sql:", Students.sql_create_table())

    students = Students(db)
    slist = students.student_list(21)

    #students.update_json_cell(415, "EXTRA", LEVEL="Gym", SEX="w")
    #print("§§§", slist[-1])

    classes = Classes(db)
    for cid, CLASS, NAME in classes.class_list():
        print(f"\n Class {CLASS}\n==============")
        for s in students.student_list(cid):
            print("  --", s)