"""
ui/dialogs/dialog_text_line.py

Last updated:  2023-10-30

Supporting "dialog" for the course editor – edit a line of text.


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

from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    ### QtGui:
    ### QtCore:
    QPoint,
    Slot,
    ### other
    load_ui,
)

### -----


def textLineDialog(
    start_value: str,
    default: str = "",
    title: str = None,
    parent: Optional[QWidget] = None,
    pos: Optional[QPoint] = None,
) -> Optional[str]:

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = ui.textline.text()

    @Slot()
    def reset():
        ui.textline.clear()
        ui.accept()

    @Slot(str)
    def on_textline_textEdited(text):
        if start_value:
            pb_accept.setDisabled(text == start_value)
        else:
            pb_accept.setDisabled(text == start_value or text == default)

    ##### functions #####

    ##### dialog main ######

    ui = load_ui("dialog_text_line.ui", parent, locals())
    pb_reset = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Reset
    )
    pb_reset.clicked.connect(reset)
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )

    # Data initialization
    #suppress_events = True
    if title:
        ui.label.setText(title)
    ui.textline.setText(start_value or default)
    if not start_value:
        pb_reset.hide()
    pb_accept.setDisabled(True)
    #suppress_events = False
    # In case a screen position was passed in:
    if pos:
        ui.move(pos)
    # Activate the dialog
    result = None
    #ui.textline.setFocus()
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.db_access import open_database
    open_database()

    print("----->", textLineDialog(start_value=""))
    print("----->", textLineDialog(start_value="Hello World!"))
