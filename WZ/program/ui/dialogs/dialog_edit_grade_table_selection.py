"""
ui/dialogs/dialog_edit_grade_table_selection.py

Last updated:  2024-02-10

Supporting "dialog" for the grades manager – edit the "occasion" + group
pairs and their associated report types and templates.


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
#T = Tr("ui.dialogs.dialog_edit_grade_table_selection")

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

from core.basic_data import get_database
from core.classes import format_class_group, GROUP_ALL
import grades.grade_tables

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

def editGradeTableSelectionDialog(
    start_value: list,
    class_groups: list,
    basic_entries: list[str] = None,
    parent: Optional[QWidget] = None,
) -> Optional[str]:

    if basic_entries is None:
        # Prefix "no group" and "whole class" entries
        basic_entries = ['', GROUP_ALL]

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = groups

    @Slot(str)
    def on_occasion_list_currentTextChanged(text):
        cgmap = report_types[text]
        ui.group_list.clear()
        ui.group_list.addItems(cgmap)

    @Slot(int, int)
    def _on_class_table_cellChanged(row, col):
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
                g = cb.currentText().split("=", 1)[0]
                groups.append((rec[0], g))
                cglist.append(format_class_group(rec[1], g))
        #print("§evaluate:", groups, "=?", groups0)
        ui.value.setText(", ".join(cglist))
        pb_accept.setEnabled(dict(groups) != groups0)

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_edit_grade_table_selection.ui", None, locals())
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

    db = get_database()
    report_types = db.table("GRADE_REPORT_CONFIG")._template_info
    ui.occasion_list.clear()
    ui.occasion_list.addItems(report_types)

    # Populate the class combobox
    class_list = db.table("CLASSES").class_list()
    print("???", class_list)
    ui.combo_classes.clear()
    ui.combo_classes.addItems(c for _, c, _ in class_list)

#+++++++++++++


    result = None
    # Use a <dict> to check for changed entries because this will
    # ignore the order (a list comparison wouldn't).
    suppress_events = False
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    ui.resize(0, 0)
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":

    print("\n----->", editGradeTableSelectionDialog(
        start_value = [],
        class_groups = [],
        basic_entries = None,
        parent = None,
    ))
