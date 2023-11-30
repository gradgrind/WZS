"""
ui/dialogs/dialog_workload.py

Last updated:  2023-11-30

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

#from core.base import TRANSLATIONS
#T = TRANSLATIONS("ui.dialogs.dialog_workload")

### +++++

from typing import Optional

from core.db_access import db_TableRow
from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    QHeaderView,
    ### QtGui:
    ### QtCore:
    Qt,
    Slot,
    ### other
    load_ui,
)
from ui.table_support import Table

### -----

#TODO ...
def workloadDialog(
    start_value: Optional[db_TableRow] = None,  # a COURSE_BASE row
    parent: Optional[QWidget] = None,
) -> Optional[str]:

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
#        result = new_block

    @Slot(int, int)
    def changed_pay_factor(row, column):
        if suppress_handlers: return
        print(
            f"§TODO: changed_pay_factor ({row}):",
            ui.teacher_table.item(row, column).text()
        )

    ##### functions #####

    def shrink():
        ui.resize(0, 0)

    def reset():
        assert False, "TODO: reset"

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
    ui.teacher_table.cellChanged.connect(changed_pay_factor)
    shrink() # minimize dialog window


    ## Data initialization
#    block_map = blocks_info()
    suppress_handlers = True

    table.set_row_count(1)
    ui.teacher_table.item(0, 0).setFlags(Qt.ItemFlag.NoItemFlags)
    ui.teacher_table.item(0, 0).setText("Fred Bloggs")
    ui.teacher_table.item(0, 1).setData(Qt.ItemDataRole.EditRole, 1.0)

    suppress_handlers = False

    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    result = None
    #widget.setFocus()
    ui.exec()
    return result




# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    get_database()
    workloadDialog()
