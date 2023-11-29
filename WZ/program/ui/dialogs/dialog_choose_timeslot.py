"""
ui/dialogs/dialog_choose_timeslot.py

Last updated:  2023-11-31

Supporting "dialog" for the course editor – select a timeslot.


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
#T = TRANSLATIONS("ui.dialogs.dialog_text_line")

### +++++

from typing import Optional

from core.time_slots import TimeSlots
from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    QPushButton,
    QButtonGroup,
    ### QtGui:
    ### QtCore:
    QPoint,
    Slot,
    ### other
    load_ui,
)

### -----


def chooseTimeslotDialog(
    parent: Optional[QWidget] = None,
    pos: Optional[QPoint] = None,
) -> Optional[str]:

    ##### slots #####

    @Slot(int)
    def choose(i):
        nonlocal result
        result = i
        #print("!!!", timeslots.timeslots[i].NAME)
        ui.accept()

    @Slot()
    def reset():
        nonlocal result
        result = 0
        ui.accept()

    ##### functions #####

    ##### dialog main ######

    ui = load_ui("dialog_choose_timeslot.ui", parent, locals())
    pb_reset = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Reset
    )
    pb_reset.clicked.connect(reset)

    buttons = QButtonGroup(ui.frame)
    buttons.idClicked.connect(choose)
    timeslots = TimeSlots.read()

    for i, ts in enumerate(timeslots.timeslots):
        if i == 0: continue
        col = ts.day
        row = ts.period
        w = QPushButton(ts.NAME)
        buttons.addButton(w, i)
        ui.grid.addWidget(w, ts.period, ts.day)

    # In case a screen position was passed in:
    if pos:
        ui.move(pos)
    # Activate the dialog
    result = None
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.db_access import open_database
    open_database()

    print("----->", chooseTimeslotDialog())
