"""
ui/dialogs/dialog_course_groups.py

Last updated:  2023-12-09

Supporting "dialog" for the course editor – edit the groups in a course.


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
#T = TRANSLATIONS("ui.dialogs.dialog_course_groups")

### +++++

from typing import Optional

from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    QTableWidgetItem,
    QComboBox,
    ### QtGui:
    ### QtCore:
    Qt,
    Slot,
    ### other
    load_ui,
)

from core.base import format_class_group

### -----

#class ComboBoxDelegate(QStyledItemDelegate):
#    def __init__(self, model):
#        super().__init__()
#        self.model = model
#
#    def createEditor(self, parent, option, index):
#        widget = QComboBox(parent)
#        widget.addItems(['', 'Cat', 'Dog'])
#        return widget
#
#    def setModelData(self, widget, model, index):
#        self.model.setData(index, widget.currentIndex())

def courseGroupsDialog(
    start_value: list,
    class_groups: list,
    basic_entries: list[str] = None,
    parent: Optional[QWidget] = None,
) -> Optional[str]:

    if basic_entries is None:
        # Prefix "no group" and "whole class" entries
        basic_entries = ['', '*']

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = groups

    @Slot(int, int)
    def on_class_table_cellChanged(row, col):
        nonlocal suppress_events
        if suppress_events: return
        if col == 0:
            cb = ui.class_table.cellWidget(row, 1)
            item = ui.class_table.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                cb.setEnabled(True)
                # The whole class should be at index 1, select this by default
                suppress_events = True
                cb.setCurrentIndex(1)
                suppress_events = False
            else:
                cb.setEnabled(False)
                suppress_events = True
                cb.setCurrentIndex(0)
                suppress_events = False
            evaluate()

    # Actually not a slot, it is called via a lambda function
    def cb_changed(row, text):
        if suppress_events: return
        evaluate()
        #print("§cb_changed:", row, text)

    ##### functions #####

    def evaluate():
        groups.clear()
        cglist = []
        for row, rec in enumerate(class_groups):
            item = ui.class_table.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                # Include this row
                cb = ui.class_table.cellWidget(row, 1)
                g = cb.currentText()
                groups.append((rec[0], g))
                cglist.append(format_class_group(rec[1], g))
        #print("§evaluate:", groups, "=?", groups0)
        ui.value.setText(", ".join(cglist))
        pb_accept.setEnabled(groups != groups0)

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_course_groups.ui", None, locals())
#    delegate = ComboBoxDelegate()
#    ui.class_table.setItemDelegateForColumn(1, delegate)
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )

    # Data initialization
    suppress_events = True
#    if title:
#        ui.label.setText(title)
#    ui.textline.setText(start_value or default)
    ui.class_table.setRowCount(0)
    ui.class_table.setRowCount(len(class_groups))
    class2row = {}
    for row, rec in enumerate(class_groups):
        class2row[rec[0]] = row
        # Set class field
        item = QTableWidgetItem(rec[1])
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setCheckState(Qt.CheckState.Unchecked)
        ui.class_table.setItem(row, 0, item)
        # Initialize choice field entries
        cb = QComboBox()
        cb.setEnabled(False)
        cb.currentTextChanged.connect(lambda text, r=row: cb_changed(r, text))
        cb.addItems(basic_entries)
        for div in rec[2]:
            cb.insertSeparator(cb.count())
            cb.addItems(div)
        ui.class_table.setCellWidget(row, 1, cb)
    # Set initial selection
    for ci, g in start_value:
        row = class2row[ci]
        item = ui.class_table.item(row, 0)
        item.setCheckState(Qt.CheckState.Checked)
        cb = ui.class_table.cellWidget(row, 1)
        cb.setCurrentText(g)
        cb.setEnabled(True)

    result = None
    groups0 = []
    groups = []
    evaluate()
    for g in groups:
        groups0.append(g)
    pb_accept.setEnabled(False)
    suppress_events = False
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    class_groups = [
        (1, "01G", [("A", "B")],),
        (7, "05G", [("A", "B")]),
        (8, "05K", []),
        (12, "10G", [("A", "BG", "R", "G=A+BG", "B=BG+R"), ("X", "Y"),]),
    ]

    start_groups = [(1, "B"), (8, "*"),]

    '''
    from core.db_access import get_database
    from core.classes import Classes

    db = get_database()
    classes = Classes(db)
    class_groups = [
        (rec.id, rec.CLASS, rec.DIVISIONS) for rec in classes.records
        if rec.id
    ]
    '''

    print("\n?class_groups:")
    for cg in class_groups:
        print("   --", cg)

    print("\n----->", courseGroupsDialog(
        start_value = start_groups,
        class_groups=class_groups
    ))
