"""
core/students.py - last updated 2024-02-21

Manage students data.

#TODO: update to suit new db

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
    setup(basedir)

#from core.base import Tr
#T = Tr("core.students")

### +++++

from core.basic_data import DB, DB_Table

### -----


class Students(DB_Table):
    __slots__ = ()
    _table = "STUDENTS"
    order = "SORTNAME"
#?    null_entry = {"SID": "", "NAME": "", "SORTING": ""}

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
        for node, id in self.records(Class_id = class_id):
            if (not group) or group in node.GROUPS.split():
                slist.append(node)
        return slist


DB_Table.add_table(Students)


def compare_update(
    newdata: list[dict[str, str | int]]
) -> tuple[
    list[dict],     # new students (field mapping)
    list[tuple[int, list[tuple[str, str | int]]]],  # changed fields
    list[int]       # students to remove (id)
]:
    """Compare the new data with the existing data and compile lists
    of changes. There are three types of change:
        - new student
        - student to remove (students shouldn't be removed within a
          school-year, just marked in DATE_EXIT, but this could be
          needed for patching or migrating to a new year)
        - field(s) changed.
    The new data is supplied as a mapping: {PID: {field: value}}
    Return lists for each of the types of changes.
    """
    new_list, delta_list, remove_list = [], [], []
    ## Get a mapping of all current pupils: {pid: (pupil-data, pupil-id)}
    students = DB("STUDENTS")
    current_students = {
        node.PID: (node, id)
        for node, id in students.records()
    }
    first_day = DB().CALENDAR.DATE_FIRST
    ## Compare new data with old
    for pmap in newdata:
        # Skip students who have left
        date_exit = pmap["DATE_EXIT"]
        if date_exit and date_exit < first_day:
            continue
        try:
            olddata, id = current_students.pop(pmap["PID"])
        except KeyError:
            # New student
            new_list.append(pmap)
            continue
        # Compare the fields of the old pupil-data with the new ones.
        # Build a list of pairs detailing the deviating fields:
        #       [(field, new-value), ...]
        # Only the fields of the new data are taken into consideration.
        delta = []
        for k, v in pmap.items():
            if v != olddata[k]:
                delta.append((k, v))
        if delta:
            delta_list.append((id, delta))
    ## Add removed pupil-ids to list
    for pid, pdata in current_students.items():
        remove_list.append(pdata[1])
    return new_list, delta_list, remove_list


def update_classes(
    new_list: list[dict],   # new students (field mapping)
    delta_list: list[tuple[int, list[tuple[str, str | int]]]],
    # ... changed fields
    remove_list: list[int]  # students to remove (id)
):
    """Apply the changes in the supplied lists to the pupil data.
    The entries are basically those generated by <compare_update>,
    but it would be possible to insert a filtering step before
    calling this function.
    """
    db = DB()
    for pdata in new_list:
        # Add a new student
        db.add_node("STUDENTS", **pdata)
    for id, delta in delta_list:
        node = db.nodes[id]
        for k, v in delta:
            node[k] = v
    for id in remove_list:
        db.delete_node(id)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    import core.classes     # noqa: F401    – to initialize CLASSES
    students = DB("STUDENTS")
    classes = DB("CLASSES")
    cl = classes.class2id["12"]
    for s in students.student_list(cl, "R"):
        print("  --", s)

    for cid, CLASS, NAME in classes.class_list():
        print(f"\n Class {CLASS}\n==============")
        for s in students.student_list(cid):
            print("  --", s)

    print("\n  ***** DELTA *****")
    from core.base import DATAPATH
    from local.niwa.raw_students import read_raw_students_data

    fpath = DATAPATH("test_students_data.ods", "working_data")
    records = read_raw_students_data(fpath, classes.class2id)
    changes = compare_update(records)
    for c in changes[1]:
        print("  DELTA ::", c)
    for c in changes[0]:
        print("  NEW ::", c)
    for c in changes[2]:
        print("  REMOVE ::", c)

#TODO: Test this
#    update_classes(changes)
