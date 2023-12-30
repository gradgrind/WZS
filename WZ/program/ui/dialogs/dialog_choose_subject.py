"""
ui/dialogs/dialog_choose_subject.py

Last updated:  2023-12-30

Supporting "dialog" – select a subject.


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
#T = Tr("ui.dialogs.dialog_choose_subject")

### +++++

from typing import Optional

from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    ### QtGui:
    ### QtCore:
    Slot,
    ### other
    load_ui,
)

### -----

def chooseSubjectDialog(
    start_value: int,
    subjects: list[tuple[int, str, str]],
    parent: Optional[QWidget] = None,
) -> Optional[str]:

    ##### slots #####

    @Slot(int)
    def on_cb_subject_currentIndexChanged(row):
        if suppress_events: return
        nonlocal result
        result = subjects[ui.cb_subject.currentIndex()][0]
        ui.accept()

    ##### functions #####

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_choose_subject.ui", None, locals())
    # Data initialization
    suppress_events = True
    row = combotable2(ui.cb_subject, subjects, start_value)
    # Set initial selection
    ui.cb_subject.setCurrentIndex(row)
    result = None
    suppress_events = False

    # In case a screen position was passed in:
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    ui.exec()
    return result


### A possibility of displaying the popup list as a table.
from ui.ui_base import (
#    QStandardItemModel,
#    QStandardItem,
#    QTableView,
    QAbstractItemView,

    QTableWidget,
    QTableWidgetItem,
)
'''
# Using QTableView with QStandardItemModel ...
def combotable(combobox, datalist, v0):
    model = QStandardItemModel(len(datalist), 3)
    #model.setHorizontalHeaderLabels(("title", "name"))
    row = -1
    for i in range(model.rowCount()):
        datarow = datalist[i]
        if datarow[0] == v0:
            row = i
        for j in range(model.columnCount()):
            it = QStandardItem(datarow[j])
            model.setItem(i, j, it)
    combobox.setModel(model)
    combobox.setModelColumn(2)
    view = QTableView(parent = combobox)
    viewhh = view.horizontalHeader()
    viewhh.setStretchLastSection(True)
    viewhh.hide()
    view.verticalHeader().hide()
    combobox.setView(view)
    view.hideColumn(0)
    view.setSelectionBehavior(QAbstractItemView.SelectRows)
    #view.setFixedWidth(350)
    return row
'''

# Using QTableWidget ...
def combotable2(combobox, datalist, v0):
    table = QTableWidget(len(datalist), 3, combobox)
    row = -1
    for i in range(table.rowCount()):
        rowdata = datalist[i]
        if rowdata[0] == v0:
            row = i
        for j in range(table.columnCount()):
            it = QTableWidgetItem(rowdata[j])
            table.setItem(i, j, it)
    combobox.setModel(table.model())
    combobox.setModelColumn(2)
    viewhh = table.horizontalHeader()
    viewhh.setStretchLastSection(True)
    viewhh.hide()
    table.verticalHeader().hide()
    combobox.setView(table)
    table.hideColumn(0)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    #table.setFixedWidth(350)
    return row


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    slist = [
        (1, "Awt", "Arbeit-Wirtschaft-Technik"),
        (5, "En", "Englisch"),
        (7, "Fr", "Französisch"),
        (8, "Ges", "Geschichte"),
        (12, "Ku", "Kunst"),
    ]

    '''
    from core.basic_data import get_database
    from core.subjects import Subjects

    db = get_database()
    subjects = Subjects(db)
    slist = subjects.subject_list()
    '''

    print("\n?subjects:")
    for s in slist:
        print("   --", s)

    print("\n----->", chooseSubjectDialog(
        start_value = -1,
        subjects = slist
    ))
    print("\n----->", chooseSubjectDialog(
        start_value = 5,
        subjects = slist
    ))
