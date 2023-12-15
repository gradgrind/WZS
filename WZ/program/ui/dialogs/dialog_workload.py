"""
ui/dialogs/dialog_workload.py

Last updated:  2023-12-15

Supporting "dialog" for the course editor – set workload/pay.


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

from core.base import TRANSLATIONS
T = TRANSLATIONS("ui.dialogs.dialog_workload")

### +++++

from typing import Optional

from core.base import REPORT_ERROR
from core.course_base import COURSE_LINE, print_workload
from core.basic_data import CONFIG, print_fix
from core.teachers import Teachers
from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    QHeaderView,
    QStyledItemDelegate,
    QDoubleSpinBox,
    ### QtGui:
    ### QtCore:
    Qt,
    Slot,
    ### other
    load_ui,
)
from ui.table_support import Table

### -----


class SpinDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QDoubleSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(0.0)
        editor.setMaximum(20.0)
        editor.setDecimals(CONFIG.DECIMAL_PLACES)
        return editor

#    def setEditorData(self, editor, index):
#        value = index.model().data(index, Qt.ItemDataRole.EditRole)
#        editor.setValue(float(value))

    def displayText(self, value, locale):
        return print_fix(value)


def workloadDialog(
    start_value: Optional[COURSE_LINE] = None,  # a COURSE_BASE row
    nlessons: int = 0,
    parent: Optional[QWidget] = None,
) -> Optional[list[tuple[int, float]]]:

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = delta

    @Slot(int, int)
    def changed_pay_factor(row, column):
        if suppress_handlers: return
        if column == 1:
            item = ui.teacher_table.item(row, column)
            val = item.data(Qt.ItemDataRole.EditRole)
            t, _ = teacher_list[row]
            teacher_list[row] = (t, val)
            value_changed()

    @Slot(bool)
    def on_rb_lessons_toggled(on):
        if on:
            ui.block_count.setEnabled(False)
            ui.block_count.setValue(1.0)
            ui.workload_label.setText(T["VIA_LESSONS"])
            if suppress_handlers: return
            value_changed()

    @Slot(bool)
    def on_rb_direct_toggled(on):
        if on:
            ui.block_count.setEnabled(True)
            ui.workload_label.setText(T["DIRECT"])
            if suppress_handlers: return
            value_changed()

    @Slot(float)
    def on_workload_valueChanged(value):
        if suppress_handlers: return
        value_changed()

    @Slot(float)
    def on_block_count_valueChanged(value):
        if suppress_handlers: return
        value_changed()

    ##### functions #####

    def shrink():
        ui.resize(0, 0)

    def reset():
        """Set WORKLOAD to 0.0, BLOCK_COUNT to 1.0 and all
        PAY_FACTORs to 1.0.
        """
        nonlocal delta
        delta = null_delta
        ui.accept()

    def value_changed():
        """Collect modified parameters in the list <delta>, which contains
        (key, value) pairs:
            key -2: BLOCK_COUNT has changed,
            key -1: WORKLOAD has changed,
            key >=0: PAY_FACTOR has changed for the indexed teacher (in
                the course).
        """
        workload = ui.workload.value()
        if ui.rb_lessons.isChecked() and workload > 0.0:
            workload = - workload
        bcount = ui.block_count.value()
        ui.payment.setText(print_workload(
            workload, bcount, nlessons, teacher_list
        ))
        # Compare with original values
        delta.clear()
        # ... and with "null" values
        if workload != workload0:
            delta.append((-1, workload))
        if bcount != block_count0:
            delta.append((-2, bcount))
        for i, t in enumerate(teacher_list):
            pf = t[1]
            if pf != pay_factor_list0[i]:
                delta.append((i, pf))
        pb_accept.setEnabled(bool(delta))

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_workload.ui", None, locals())
    pb_accept = ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
    pb_reset = ui.buttonBox.button(QDialogButtonBox.StandardButton.Reset)
    pb_reset.clicked.connect(reset)
    table = Table(ui.teacher_table)
    hh = ui.teacher_table.horizontalHeader()
    hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    delegate = SpinDelegate()
    ui.teacher_table.setItemDelegateForColumn(1, delegate)
    ui.teacher_table.cellChanged.connect(changed_pay_factor)
    shrink() # minimize dialog window

    ## Data initialization
    suppress_handlers = True

    teacher_list = []
    pay_factor_list0 = []
    # A negative WORKLOAD indicates a lesson-count factor
    if start_value:
        workload0 = start_value.course.Lesson_block.WORKLOAD
        if workload0 < 0.0:
            if start_value.course.BLOCK_COUNT != 1.0:
                REPORT_ERROR(T["BLOCK_COUNT_NOT_1"])
                start_value.course._write("BLOCK_COUNT", "1")
            block_count0 = 1.0
            ui.workload.setValue(- workload0)
            ui.rb_lessons.setChecked(True)
            on_rb_lessons_toggled(True)
        else:
            block_count0 = start_value.course.BLOCK_COUNT
            ui.block_count.setValue(block_count0)
            ui.workload.setValue(workload0)
            ui.rb_direct.setChecked(True)
            on_rb_direct_toggled(True)
        table.set_row_count(len(start_value.teacher_list))
        for row, ct in enumerate(start_value.teacher_list):
            name = Teachers.get_name(ct.Teacher)
            ui.teacher_table.item(row, 0).setFlags(Qt.ItemFlag.NoItemFlags)
            ui.teacher_table.item(row, 0).setText(name)
            item1 = ui.teacher_table.item(row, 1)
            item1.setData(Qt.ItemDataRole.EditRole, ct.PAY_FACTOR)
            pf = item1.data(Qt.ItemDataRole.EditRole)
            teacher_list.append((ct.Teacher.TID, pf))
            pay_factor_list0.append(pf)
    else:
        # for testing only
        workload0 = -1.0 if nlessons else 0.0
        if workload0 < 0.0:
            ui.workload.setValue(- workload0)
            block_count0 = 1.0
            ui.rb_lessons.setChecked(True)
            on_rb_lessons_toggled(True)
        else:
            ui.block_count.setValue(1.0)
            block_count0 = 1.0
            ui.workload.setValue(workload0)
            ui.rb_direct.setChecked(True)
            on_rb_direct_toggled(True)
        table.set_row_count(1)
        ui.teacher_table.item(0, 0).setFlags(Qt.ItemFlag.NoItemFlags)
        ui.teacher_table.item(0, 0).setText("Fred Bloggs")
        item1 = ui.teacher_table.item(0, 1)
        item1.setData(Qt.ItemDataRole.EditRole, 1.0)
        pf = item1.data(Qt.ItemDataRole.EditRole)
        teacher_list.append(("FB", pf))
        pay_factor_list0.append(pf)
    ## Set initial "changed" status
    delta = []
    # Determine whether the reset button should be shown. If so, <null_delta>
    # will be the return value when it is pressed.
    null_delta = []  
    if workload0 != 0.0:
        null_delta.append((-1, 0.0))
    if block_count0 != 1.0:
        null_delta.append((-2, 1.0))
    for i, pf in enumerate(pay_factor_list0):
        if pf != 1.0:
            null_delta.append((i, 1.0))
    pb_reset.setVisible(bool(null_delta))
    result = None
    value_changed()
    suppress_handlers = False
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    #widget.setFocus()
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    get_database()
    print("----->", workloadDialog())
    print("----->", workloadDialog(nlessons = 3))
