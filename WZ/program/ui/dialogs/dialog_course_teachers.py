"""
ui/dialogs/dialog_course_teachers.py

Last updated:  2024-01-06

Supporting "dialog" for the course editor – edit the teachers of a course.


=+LICENCE=============================
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
#T = Tr("ui.dialogs.dialog_course_teachers")

### +++++

from typing import Optional

from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    QTableWidgetItem,
    ### QtGui:
    ### QtCore:
    QObject,
    Qt,
    Slot,
    QEvent,
    ### other
    load_ui,
)

NO_REPORTS = "☐"
WITH_REPORTS = "☑"

### -----


class EventFilter(QObject):
    """Implement an event filter for key presses on the table.
    """
    def __init__(self, table, reports):
        super().__init__()
        table.installEventFilter(self)
        self.table = table
        self.reports = reports

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Space:
                row = self.table.currentRow()
                item = self.table.item(row, 0)
                if item.checkState() == Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setCheckState(Qt.CheckState.Checked)
                return True
            if key == Qt.Key.Key_Plus:
                self.set_report(True)
                return True
            if key == Qt.Key.Key_Minus:
                self.set_report(False)
                return True
        # otherwise standard event processing
        return False

    def set_report(self, on):
        row = self.table.currentRow()
        item0 = self.table.item(row, 0)
        if item0.checkState() != Qt.CheckState.Checked:
            return
        item = self.table.item(row, 1)
        if on:
            self.reports[row] = True
            item.setText(WITH_REPORTS)
        else:
            self.reports[row] = False
            item.setText(NO_REPORTS)


def courseTeachersDialog(
    start_value: list,
    teachers: list,
    parent: Optional[QWidget] = None,
) -> Optional[str]:

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = chosen

    @Slot(int, int)
    def on_teacher_table_cellChanged(row, col):
        nonlocal suppress_events
        if suppress_events: return
        if col == 0:
            item = ui.teacher_table.item(row, 0)
            item1 = ui.teacher_table.item(row, 1)
            suppress_events = True
            if item.checkState() == Qt.CheckState.Checked:
                reports[row] = True
                item1.setText(WITH_REPORTS)
            else:
                reports[row] = False
                item1.setText(NO_REPORTS)
            suppress_events = False
        evaluate()

    @Slot(int, int, int, int)
    def on_teacher_table_currentCellChanged(r, c, r0, c0):
        """This is to keep the current cell in the first column.
        """
        if c > 0:
            ui.teacher_table.setCurrentCell(r, 0)

    @Slot(int, int)
    def on_teacher_table_cellClicked(r, c):
        if c == 1:
            event_filter.set_report(not reports[r])

    ##### functions #####

    def evaluate():
        chosen.clear()
        tidlist = []
        for row, rec in enumerate(teachers):
            item = ui.teacher_table.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                # Include this row
                z = reports[row]
                chosen.append((rec[0], z))
                #chosen.append(rec[0])
                tidlist.append(rec[1] if z else f"({rec[1]})")
                #tidlist.append(rec[1])
        #print("§evaluate:", chosen, "=?", chosen0)
        ui.value.setText(", ".join(tidlist))
        pb_accept.setEnabled(chosen != chosen0)

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_course_teachers.ui", None, locals())
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )
    reports = []
    event_filter = EventFilter(ui.teacher_table, reports)

    # Data initialization
    suppress_events = True
    ui.teacher_table.setRowCount(0)
    ui.teacher_table.setRowCount(len(teachers))
    teacher2row = {}
    for row, rec in enumerate(teachers):
        teacher2row[rec[0]] = row
        reports.append(False)
        # Set fields
        item = QTableWidgetItem(rec[1])
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setCheckState(Qt.CheckState.Unchecked)
        ui.teacher_table.setItem(row, 0, item)
        item = QTableWidgetItem(NO_REPORTS)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        ui.teacher_table.setItem(row, 1, item)
        item = QTableWidgetItem(rec[2])
        ui.teacher_table.setItem(row, 2, item)
    # Set initial selection
    for ti, ri in start_value:
        row = teacher2row[ti]
        item = ui.teacher_table.item(row, 0)
        item.setCheckState(Qt.CheckState.Checked)
        ui.teacher_table.setCurrentCell(row, 0) # should scroll to line
        event_filter.set_report(ri)

    result = None
    chosen0 = []
    chosen = []
    evaluate()
    for t in chosen:
        chosen0.append(t)
    pb_accept.setEnabled(False)
    suppress_events = False

    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
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

    t0 = [(1, True), (8, False),]

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
