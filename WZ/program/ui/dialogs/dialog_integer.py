"""
ui/dialogs/dialog_integer.py

Last updated:  2023-12-01

Supporting "dialog" for the course editor – edit an integer (e.g. lesson
length).


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
#T = TRANSLATIONS("ui.dialogs.dialog_integer")

### +++++

from typing import Optional

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


def integerDialog(
    start_value: Optional[int] = None,
    default: Optional[int] = None,
    title: str = None,
    min: int = 0,
    max: int = 9,
    parent: Optional[QWidget] = None,
) -> Optional[int]:

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = ui.number.value()

    @Slot()
    def reset():
        if default is not None:
            ui.number.setValue(default)
        ui.accept()

    @Slot(int)
    def on_number_valueChanged(value: int):
        if suppress_events: return
        pb_accept.setEnabled(value != start_value)

    ##### functions #####

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_integer.ui", None, locals())
    suppress_events = True
    ui.number.setMinimum(min)
    ui.number.setMaximum(max)
    pb_reset = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Reset
    )
    pb_reset.clicked.connect(reset)
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )
    ## Data initialization
    if title:
        ui.label.setText(title)
    if default is None:
        v0 = min if start_value is None else start_value
    else:
        v0 = default if start_value is None else start_value
    ui.number.setValue(v0)
    pb_reset.setVisible(default is not None and start_value != default)
    pb_accept.setDisabled(True)
    suppress_events = False
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    result = None
    #ui.textline.setFocus()
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    print("----->", integerDialog())
    print("----->", integerDialog(start_value=2, default=1))
