"""
ui/dialogs/dialog_new_course.py

Last updated:  2023-12-30

Supporting "dialog" for the course editor – prepare a new course.


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

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

#from core.base import Tr
#T = Tr("ui.dialogs.dialog_new_course")

### +++++

from typing import Optional

from core.db_access import db_TableRow
from core.basic_data import get_database
from core.classes import format_class_group
from core.course_base import BLOCK
from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    ### QtGui:
    ### QtCore:
    Slot,
    ### other
    load_ui,
)
from ui.dialogs.dialog_choose_subject import chooseSubjectDialog
from ui.dialogs.dialog_course_groups import courseGroupsDialog
from ui.dialogs.dialog_course_teachers import courseTeachersDialog
from ui.dialogs.dialog_block_name import blockNameDialog

### -----


def newCourseDialog(
    start_subject: int = 0,
    start_teachers: Optional[list[tuple[int, bool]]] = None,
    start_groups: Optional[list[tuple[int, str]]] = None,
    block: Optional[db_TableRow] = None,    # a BLOCK_LESSONS row
    parent: Optional[QWidget] = None,
) -> Optional[tuple[
    int,
    list[tuple[int, bool]],
    list[tuple[int, str]],
    BLOCK
]]:
    """Allow editing of the subject, teacher and group fields for
    a new course.
        <start_subject> is the db id of the initial subject.
        <start_teachers> is a list of the initial teachers:
            (int: db teacher id, bool: available for reports).
        <start_groups> is a list of the initial groups:
            (int: db class id, str: group-tag).
        <block> is a row of the BLOCK_LESSONS table, allowing easy
            addition of the new course to an existing block.
    """

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = (
            subject_id,
            course_teachers,
            course_groups,
            current_block or BLOCK()
        )

    @Slot()
    def on_block_clicked():
        nonlocal current_block
        current_block = blockNameDialog()
        show_block()

    @Slot()
    def on_subject_clicked():
        nonlocal subject_id
        s = chooseSubjectDialog(
            start_value = subject_id,
            subjects = subjects.subject_list(),
        )
        if s is not None:
            subject_id = s
            show_subject()
            acceptable()

    @Slot()
    def on_students_clicked():
        class_groups = [
            (rec.id, rec.CLASS, rec.DIVISIONS)
            for rec in classes.records
            if rec.id
        ]
        cglist = courseGroupsDialog(
            start_value = course_groups,
            class_groups = class_groups,
        )
        if cglist is not None:
            #print("§EDITED Groups:", course_groups, "->", cglist)
            course_groups.clear()
            for cg in cglist:
                course_groups.append(cg)
            show_students()
            acceptable()

    @Slot()
    def on_teachers_clicked():
        tlist = courseTeachersDialog(
            start_value = course_teachers,
            teachers = teachers.teacher_list(),
        )
        if tlist is not None:
            #print("§EDITED Teachers:", course_teachers, "->", tlist)
            course_teachers.clear()
            for t in tlist:
                course_teachers.append(t)
            show_teachers()
            acceptable()

    ##### functions #####

    def shrink():
        ui.resize(0, 0)

    def show_subject():
        ui.subject.setText(subjects[subject_id].NAME)

    def show_teachers():
        ui.teachers.setText(
            ", ".join(teachers[t[0]].TID for t in course_teachers)
        )

    def show_students():
        ui.students.setText(", ".join(
            format_class_group(classes[c].CLASS, g)
            for c, g in course_groups
        ))

    def show_block():
        if current_block is None:
            ui.block.setText("")
        else:
            ui.block.setText(current_block.key())

    def acceptable():
        pb_accept.setEnabled(bool(
            subject_id and (course_groups or course_teachers)
        ))

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_new_course.ui", None, locals())
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )
    #suppress_events = True
    ## Data initialization
    db = get_database()
    subjects = db.table("SUBJECTS")
    classes = db.table("CLASSES")
    teachers = db.table("TEACHERS")
    # Current data
    subject_id = start_subject
    course_teachers = start_teachers or []
    course_groups = start_groups or []
    if block is not None and block.BLOCK:
        current_block = BLOCK.read(block.BLOCK, block.id)
    else:
        current_block = None
    # Initialize display
    show_subject()
    show_teachers()
    show_students()
    show_block()
    acceptable()
    #pb_accept.setDisabled(True)
    #suppress_events = False
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    result = None
    shrink()
    pb_accept.setFocus()
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    print("----->", newCourseDialog())
