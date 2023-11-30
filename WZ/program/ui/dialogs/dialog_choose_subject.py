"""
ui/dialogs/dialog_choose_subject.py

Last updated:  2023-11-29

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

#from core.base import TRANSLATIONS, REPORT_ERROR
#T = TRANSLATIONS("ui.dialogs.dialog_choose_subject")

### +++++

from typing import Optional

from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    ### QtGui:
    ### QtCore:
    QObject,
    QEvent,
    Qt,
    Slot,
    ### other
    load_ui,
)

### -----


class ComboBox(QObject):
    """Implement an event filter for pressing the return key on the combobox.
    Normally it would activate the pop-up, but override that here
    so that the accept key is activated (if it is enabled).
    """
    def __init__(self, cb, pb_accept):
        super().__init__()
        self.pb_accept = pb_accept
        cb.installEventFilter(self)

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Return
        ):
            if self.pb_accept.isEnabled():
                self.pb_accept.clicked.emit()
            return True
        # otherwise standard event processing
        return False


def chooseSubjectDialog(
    start_value: int,
    subjects: list[tuple[int, str, str]],
    parent: Optional[QWidget] = None,
) -> Optional[str]:

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = chosen

    @Slot(int)
    def on_cb_subject_currentIndexChanged(row):
        if suppress_events: return
        evaluate()

    ##### functions #####

    def evaluate():
        nonlocal chosen
        chosen = subjects[ui.cb_subject.currentIndex()][0]
        pb_accept.setEnabled(chosen != start_value)

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_choose_subject.ui", None, locals())
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )
    event_filter = ComboBox(ui.cb_subject, pb_accept)

    # Data initialization
    suppress_events = True

    row = combotable(ui.cb_subject, subjects, start_value)

    '''
    ui.cb_subject.clear()
    row = -1
    for id, sid, name in subjects:
        if id == start_value:
            row = ui.cb_subject.count()
        ui.cb_subject.addItem(f"{sid}: {name}")
    '''

    # Set initial selection
    ui.cb_subject.setCurrentIndex(row)

    result = None
    chosen = start_value
    pb_accept.setEnabled(False)
    suppress_events = False

    # In case a screen position was passed in:
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    ui.exec()
    return result


# A possibility of displaying the popup list as a table.
from ui.ui_base import (
    QStandardItemModel,
    QStandardItem,
    QTableView,
    QAbstractItemView,

    QTableWidget,
    QTableWidgetItem,
)
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
    combobox.setView(view)
    view.hideColumn(0)
    view.setSelectionBehavior(QAbstractItemView.SelectRows)
    #view.setFixedWidth(350)
    return row

# Similar, but more standalone and with QWidget ...
def combotable2(datalist):
    ui = load_ui("dialog_choose_subject.ui", None, locals())
    combobox = ui.cb_subject
    table = QTableWidget(len(datalist), 3, combobox)
    #table.setHorizontalHeaderLabels(("tag", "name"))
    for i in range(table.rowCount()):
        for j in range(table.columnCount()):
            it = QTableWidgetItem(datalist[i][j])
            table.setItem(i, j, it)
    combobox.setModel(table.model())
    combobox.setModelColumn(2)
    viewhh = table.horizontalHeader()
    viewhh.setStretchLastSection(True)
    viewhh.hide()
    combobox.setView(table)
    table.hideColumn(0)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    #table.setFixedWidth(350)

    ui.exec()

# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    slist = [
        (1, "Awt", "Arbeit-Wirtschaft-Technik"),
        (5, "En", "Englisch"),
        (7, "Fr", "Französisch"),
        (8, "Ges", "Geschichte"),
        (12, "Ku", "Kunst"),
    ]

#    '''
    from core.db_access import get_database
    from core.subjects import Subjects

    db = get_database()
    subjects = Subjects(db)
    slist = subjects.subject_list()
#    '''

    print("\n?subjects:")
    for s in slist:
        print("   --", s)

    combotable2(slist)
#    quit(1)

    print("\n----->", chooseSubjectDialog(
        start_value = -1,
        subjects = slist
    ))
    print("\n----->", chooseSubjectDialog(
        start_value = 5,
        subjects = slist
    ))
