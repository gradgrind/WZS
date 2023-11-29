"""
ui/dialogs/dialog_course_teachers.py

Last updated:  2023-11-18

Supporting "dialog" for the course editor – edit the teachers of a course.


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

#from core.base import TRANSLATIONS, REPORT_ERROR
#T = TRANSLATIONS("ui.dialogs.dialog_course_teachers")

### +++++

from typing import Optional

from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    QTableWidgetItem,
    ### QtGui:
    ### QtCore:
    Qt,
    QPoint,
    Slot,
    ### other
    load_ui,
)

### -----


def courseTeachersDialog(
    start_value: list,
    teachers: list,
    parent: Optional[QWidget] = None,
    pos: Optional[QPoint] = None,
) -> Optional[str]:

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = chosen

    @Slot(int, int)
    def on_teacher_table_cellChanged(row, col):
        if suppress_events: return
        evaluate()

    ##### functions #####

    def evaluate():
        chosen.clear()
        tidlist = []
        for row, rec in enumerate(teachers):
            item = ui.teacher_table.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                # Include this row
                chosen.append(rec[0])
                tidlist.append(rec[1])
        #print("§evaluate:", chosen, "=?", chosen0)
        ui.value.setText(", ".join(tidlist))
        pb_accept.setEnabled(chosen != chosen0)

    ##### dialog main ######

    ui = load_ui("dialog_course_teachers.ui", parent, locals())
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )

    # Data initialization
    suppress_events = True
    ui.teacher_table.setRowCount(0)
    ui.teacher_table.setRowCount(len(teachers))
    teacher2row = {}
    for row, rec in enumerate(teachers):
        teacher2row[rec[0]] = row
        # Set fields
        item = QTableWidgetItem(rec[1])
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setCheckState(Qt.CheckState.Unchecked)
        ui.teacher_table.setItem(row, 0, item)
        item = QTableWidgetItem(rec[2])
        ui.teacher_table.setItem(row, 1, item)
    # Set initial selection
    for ti in start_value:
        row = teacher2row[ti]
        item = ui.teacher_table.item(row, 0)
        item.setCheckState(Qt.CheckState.Checked)

    result = None
    chosen0 = []
    chosen = []
    evaluate()
    for t in chosen:
        chosen0.append(t)
    pb_accept.setEnabled(False)
    suppress_events = False

    # In case a screen position was passed in:
    if pos:
        ui.move(pos)
    # Activate the dialog
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    tlist = [
        (1, "PQ", "Peter Quincy"),
        (7, "FT", "Fabiana Tannenhäuser"),
        (8, "SUM", "Svenja Ullmann-Meyerhof"),
        (12, "KW", "Kathrin Wollemaus"),
    ]

    t0 = [1, 8,]

    '''
    from core.db_access import get_database
    from core.teachers import Teachers

    db = get_database()
    teachers = Teachers(db)
    tlist = teachers.teacher_list()
    '''

    print("\n?teachers:")
    for t in tlist:
        print("   --", t)

    print("\n----->", courseTeachersDialog(
        start_value = t0,
        teachers = tlist
    ))
