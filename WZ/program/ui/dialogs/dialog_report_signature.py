"""
ui/dialogs/dialog_report_signature.py

Last updated:  2023-12-26

Supporting "dialog" for the course editor – edit a report signature.


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

from core.base import Tr
T = Tr("ui.dialogs.dialog_report_signature")

### +++++

from typing import Optional

from core.basic_data import REPORT_ALL_NAMES
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

### -----


def reportSignatureDialog(
    start_value: str,
    teachers: list[str],
    parent: Optional[QWidget] = None,
) -> Optional[str]:

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = ui.special.text().strip()

    @Slot()
    def reset():
        ui.special.clear()
        ui.accept()

    @Slot()
    def choose_all():
        ui.special.setText(REPORT_ALL_NAMES)
        ui.accept()

    @Slot(str)
    def on_special_textEdited(text):
        text = text.strip()
        if start_value:
            pb_accept.setDisabled(
                text == ""
                or text == start_value
                or text == all_teachers
                or text == REPORT_ALL_NAMES
            )
        else:
            pb_accept.setDisabled(
                text == ""
                or text == all_teachers
                or text == REPORT_ALL_NAMES
            )

    ##### functions #####

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_report_signature.ui", None, locals())
    pb_reset = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Reset
    )
    pb_reset.clicked.connect(reset)
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )
    pb_all = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.YesToAll
    )
    pb_all.setText(T("ALL_TEACHERS"))
    pb_all.clicked.connect(choose_all)

    # Data initialization
    #suppress_events = True
    all_teachers = ", ".join(teachers)
    ui.teachers.setText(all_teachers)
    if start_value:
        if start_value == REPORT_ALL_NAMES:
            text = all_teachers
            pb_all.hide()
        else:
            text = start_value
            pb_all.setVisible(len(teachers) > 1)
        pb_reset.show()
    else:
        text = ""
        pb_all.setVisible(len(teachers) > 1)
        pb_reset.hide()
    ui.special.setText(text)
    pb_accept.setDisabled(True)
    #suppress_events = False
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    result = None
    #ui.special.setFocus()
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    print("----->", reportSignatureDialog(
        start_value = "",
        teachers = ["Petra Tack"]
    ))
    print("----->", reportSignatureDialog(
        start_value = "Hello World!",
        teachers = ["Petra Tack", "Stefan Bruch"]
    ))
    print("----->", reportSignatureDialog(
        start_value = REPORT_ALL_NAMES,
        teachers = ["Petra Tack", "Stefan Bruch"]
    ))
