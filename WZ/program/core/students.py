"""
core/students.py - last updated 2024-02-16

Manage students data.


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
    DB_FIELD_JSON,
)
from core.basic_data import CALENDAR
from core.classes import Classes

EXTRA_SCHEMA = {
    "type": "object",
    "patternProperties":
        {"^[A-Za-z_][A-Za-z0-9_]*$": {"type": "string"}},
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
                DB_FIELD_TEXT("GROUPS"),
                DB_FIELD_JSON("__EXTRA__", schema = EXTRA_SCHEMA),
            )
            return True
        return False

    def all_string_fields(self, id: int) -> dict[str, str]:
        """Return a mapping containing all pupil fields with string values,
        including a single name field for general usage (short form) as well
        as the full name.
        """
        data = self[id]
        d = {}
        for f in self.fields:
            fname = f.field
            v = getattr(data, fname)
            if isinstance(v, str):
                d[fname] = v
        d.update(data.__EXTRA__)
        d["NAME"] = self.get_name(data)
        d["FULLNAME"] = self.get_fullname(data)
        return d

    @staticmethod
    def get_name(data):
        """Return the short form of the name from the given record.
        """
        return f"{data.FIRSTNAME} {data.LASTNAME}"

    @staticmethod
    def get_fullname(data):
        """Return the full name from the given record.
        """
        return f"{data.FIRSTNAMES} {data.LASTNAME}"

    def name(self, id):
        """Return the short form of the name from the given db-id.
        """
        return self.get_name(self[id])

    def student_list(self, class_id: int, group: str = None):
        """Return an ordered list of students from the given class.
        If a group is given, include only those students who are in the group.
        """
        slist = []
        for data in self.records:
            if data.Class.id == class_id:
                if group and group not in data.GROUPS.split():
                    continue
                slist.append(data)
        return slist
#+
DB_TABLES[Students.table] = Students


def compare_update(newdata: list[dict[str, str | int]]) -> list[tuple]:
    """Compare the new data with the existing data and compile a list
    of changes. There are three types:
        - new student
        - student to remove (students shouldn't be removed within a
          school-year, just marked in DATE_EXIT, but this could be
          needed for patching or migrating to a new year)
        - field(s) changed.
    The new data is supplied as a mapping: {PID: {field: value}}
    Return a list of changes, each "change" being a tuple representing
    one of the above three types.
    """
    students_delta = []
    # Get a mapping of all current pupils: {pid: pupil-data}
    current_students = {}
    db = get_database()
    classes = db.table("CLASSES")
    students = db.table("STUDENTS")
    for kid, klass, kname in classes.class_list():
        for pdata in students.student_list(kid):
            current_students[pdata.PID] = pdata
    first_day = CALENDAR.DATE_FIRST
    for pmap in newdata:
        date_exit = pmap["DATE_EXIT"]
        if date_exit and date_exit < first_day:
            continue
        try:
            olddata = current_students.pop(pmap["PID"])
        except KeyError:
            # New pupil
            students_delta.append(("NEW", pmap))
            continue
        # Compare the fields of the old pupil-data with the new ones.
        # Build a list of pairs detailing the deviating fields:
        #       [(field, new-value), ...]
        # Only the fields of the new data are taken into consideration.
        delta = []
        for k, v in pmap.items():
            if k.endswith("_id"):
                v0 = getattr(olddata, k[:-3]).id
            else:
                v0 = getattr(olddata, k)
            if v != v0:
                delta.append((k, v))
        if delta:
            students_delta.append(("DELTA", olddata, delta))
    # Add removed pupils to list
    for pid, pdata in current_students.items():
        students_delta.append(("REMOVE", pdata))
    return students_delta


#TODO
def update_classes(changes: list[tuple]):
    """Apply the changes in the <changes> lists to the pupil data.
    The entries are basically those generated by <compare_update>,
    but it would be possible to insert a filtering step before
    calling this function.
    """
    print("\n???????????????????\n", changes)
    db = get_database()
    students = db.table("STUDENTS")
    to_add = []
    for d in changes:
        if d[0] == "NEW":
            #print("\n§§§§§ ADD", pdata)
            # Add a new student
#TODO: I can use the mapping directly if ALL fields are in it.
# That would mean dealing with that when loading the table, or else here.
# The EXTRA field would need adding. If the table can contain values from
# it, these would need to be dealt with too...
            to_add.append(d[1])


        elif d[0] == "REMOVE":
            #print("\n§§§§§ REMOVE", pdata)
            # Remove from pupils
            db_delete_rows("PUPILS", PID=pdata["PID"])
        elif d[0] == "DELTA":
            #print("\n§§§§§ UPDATE", pdata, "\n  :::", d[2])
            # Changes field values
            db_update_fields("PUPILS", d[2], PID=pdata["PID"])
        else:
            raise Bug("Bad delta key: %s" % d[0])

    if to_add:
#TODO
        students.add_records()
#?    clear_cache()


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    db = get_database()

    #print("\n?create-sql:", Students.sql_create_table())

    students = Students(db)
    #for s in students.student_list(23, "R"):
    #    print("  --", s)

    print("\n***** STUDENTS fields *****")
    for f in students.fields:
        print("  -", f.field0, f.field)

    '''
    from core.db_access import to_json
    for rec in students.records:
        x = rec.__EXTRA__
        for k, v in x.items():
            print(" --", rec.Class.CLASS, rec.id, k, v)
        try:
            g = x.pop("GROUPS")
        except KeyError:
            pass
        else:
            if g:
                db.update("STUDENTS", rec.id, "GROUPS", g)
            db.update("STUDENTS", rec.id, "__EXTRA__", to_json(x))
    quit(2)
    '''

    classes = Classes(db)
    for cid, CLASS, NAME in classes.class_list():
        print(f"\n Class {CLASS}\n==============")
        for s in students.student_list(cid):
            print("  --", s)

    print("\n  ***** DELTA *****")
    from core.base import DATAPATH
    from local.niwa.raw_students import read_raw_students_data

    classmap = {
        rec.CLASS: rec.id
        for rec in classes.records
        if rec.id > 0
    }
#    fpath = DATAPATH("test_students_data.ods", "working_data")
    fpath = DATAPATH("student_table_2024.ods", "working_data")
    records = read_raw_students_data(fpath, classmap)
    for d in compare_update(records):
        print("  ::", d)
