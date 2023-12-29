"""
ui/course_table.py

Last updated:  2023-12-29

Support functions dealing with the course table.


=+LICENCE=============================
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

=-LICENCE========================================
"""

### +++++

from typing import Optional

from core.base import REPORT_CRITICAL
from core.basic_data import get_database
from core.classes import GROUP_ALL
from core.course_base import COURSE_LINE, REPORT_WRITER

from ui.dialogs.dialog_course_groups import courseGroupsDialog
from ui.dialogs.dialog_course_teachers import courseTeachersDialog
from ui.dialogs.dialog_choose_subject import chooseSubjectDialog

DEFAULT_TEACHER_ROLE = REPORT_WRITER

### -----

class CourseTable:
    """Manage the data from the database and the display table.
    This is the connecting link.
    """
    def __init__(self, display_table):
        self.records: list[CourseTableRow] = []
        self.display_table = display_table  # course_editor::Table

    def load(self, course_list, select_course = None) -> int:
        self.display_table.set_row_count(len(course_list))
        self.records.clear()
        line = -1
        for row, cdata in enumerate(course_list):
            ctrow = CourseTableRow(cdata)
            if select_course and ctrow.course.id == select_course:
                line = row
            self.records.append(ctrow)
            for col in range(len(ctrow.fields)):
                self.display_table.write(row, col, ctrow.show_col(col))
        return line

    def edit_cell(self, row, col):
        """Activate the editor on the given cell.
        Return true if any changes are made, the main editor can then
        redisplay the current course table.
        """
        return self.records[row].edit(col)

# A cell model couples the cell's content – including its origins, editing
# and updating – with the table display.
# Clicking or pressing return on an already selected cell in the display
# should start the editor. If that is too difficult to get working properly
# (a click will change the current cell ...), it may be easier to require
# a double-click.
# Any change to the value (i.e. changes to the sources of this value) should
# trigger an update of the display.

class CourseTableRow:
    """This is basically a wrapper around the data for a single "course",
    which is provided as a <COURSE_LINE> instance. This class adds extra
    features required for the graphical interface.
    """
    def __init__(self, course: COURSE_LINE):
        self.course_line = course
        self.course = course.course
        self.group_list = course.group_list
        self.teacher_list = course.teacher_list
        self.fields = self.course_line.fields

    def show_col(self, col: int) -> str:
        return self.course_line.show(self.fields[col])

    def edit(self, col) -> Optional[str]:
        field = self.fields[col]
        if field == "Subject":
            db = get_database()
            subjects = db.table("SUBJECTS")
            s = chooseSubjectDialog(
                start_value = self.course.Subject.id,
                subjects = subjects.subject_list(),
            )
            if s is None:
                return False
            self.course._write("Subject", s)
        elif field == "Groups":
            now = [(g.Class.id, g.GROUP_TAG) for g in self.group_list]
            db = get_database()
            classes = db.table("CLASSES")
            class_groups = [
                (rec.id, rec.CLASS, rec.DIVISIONS) for rec in classes.records
                if rec.id
            ]
            cg = courseGroupsDialog(
                start_value = now,
                class_groups = class_groups,
                basic_entries = ["", GROUP_ALL]
            )
            if cg is None:
                return False
            #print("§EDITED Groups:", now, "->", cg)
            cgtable = db.table("COURSE_GROUPS")
            i = 0
            to_add = []
            for c, g in cg:
                try:
                   c0, g0 = now[i]
                except IndexError:
                    to_add.append({
                        "Course": self.course.id,
                        "Class": c,
                        "GROUP_TAG": g,
                    })
                else:
                    delta = {}
                    if c != c0:
                        delta["Class"] = c
                    if g != g0:
                        delta["GROUP_TAG"] = g
                    if delta:
                        rowid = self.group_list[i].id
                        cgtable.update_cells(rowid, **delta)
                i += 1
            if to_add:
                cgtable.add_records(to_add)
            lnow = len(now)
            if lnow > i:
                cgtable.delete_records([
                    self.group_list[j].id
                    for j in range(i, lnow)
                ])
            # Actually not necessary if rows are added or removed, because
            # the table will need to be reloaded:
            cgtable.clear_caches()
        elif field == "Teachers":
            now = [
                (t.Teacher.id, REPORT_WRITER in t.ROLE)
                for t in self.teacher_list
            ]
            db = get_database()
            teachers = db.table("TEACHERS")
            tlist = courseTeachersDialog(
                start_value = now,
                teachers = teachers.teacher_list(),
            )
            if tlist is None:
                return False
            #print("§EDITED Teachers:", now, "->", tlist)
            ttable = db.table("COURSE_TEACHERS")
            i = 0
            to_add = []
            for t, rep in tlist:
                try:
                   t0 = now[i]
                except IndexError:
                    to_add.append({
                        "Course": self.course.id,
                        "Teacher": t,
                        "PAY_FACTOR": "1",
                        "ROLE": REPORT_WRITER if rep else ""
                    })
                else:
                    if t != t0:
                        rowid = self.teacher_list[i].id
                        ttable.update_cells(
                            rowid,
                            Teacher = t,
                            ROLE = REPORT_WRITER if rep else ""
                        )
                i += 1
            if to_add:
                ttable.add_records(to_add)
            lnow = len(now)
            if lnow > i:
                ttable.delete_records([
                    self.teacher_list[j].id
                    for j in range(i, lnow)
                ])
            # Actually not necessary if rows are added or removed, because
            # the table will need to be reloaded:
            ttable.clear_caches()
        else:
            REPORT_CRITICAL(
                "Bug in course_table::CourseTableRow.edit,"
                f" unknown field: '{field}'"
            )
        return True

    def __str__(self):
        return str(self.course_line)
