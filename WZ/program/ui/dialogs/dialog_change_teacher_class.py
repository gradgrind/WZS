"""
ui/dialogs/dialog_change_teacher_class.py

Last updated:  2024-01-06

Supporting "dialog", for the course editor – change all occurrences of
a class or teacher in a courses display page.


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

from core.base import Tr
T = Tr("ui.dialogs.dialog_change_teacher_class")

### +++++

from typing import Optional

from core.base import REPORT_INFO
from core.classes import GROUP_ALL, format_class_group
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

#TODO: Do I really want to restrict class changes to a single group?

def newTeacherClassDialog(
    start_teachers: list[int],
    start_classes: list[tuple[int, str]],
    teachers: list[tuple],
    class_groups: list[tuple],
    set_teacher: bool,
    parent: Optional[QWidget] = None,
) -> Optional[str]:

    new_block = None
    result = None

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = chosen

    @Slot(bool)
    def on_rb_teacher_toggled(on):
        nonlocal suppress_events
        if suppress_events: return
        suppress_events = True
        ui.new_value.clear()
        if on:
            ui.new_value.addItems(t[2] for t in teachers)
        else:
            ui.new_value.addItems(g[2] for g in glist)
        suppress_events = False
        changed()

    @Slot(int)
    def on_combo_teacher_currentIndexChanged(i):
        if suppress_events: return
        changed()

    @Slot(int)
    def on_combo_class_currentIndexChanged(i):
        if suppress_events: return
        changed()

    @Slot(int)
    def on_new_value_currentIndexChanged(i):
        if suppress_events: return
        changed()

    ##### functions #####

    def shrink():
        ui.resize(0, 0)

    def changed():
        nonlocal chosen
        i = ui.new_value.currentIndex()
        if ui.rb_teacher.isChecked():
            i0 = ui.combo_teacher.currentIndex()
            t0 = start_teachers[i0]
            t1 = teachers[i][0]
            chosen = None if t1 == t0 else (True, t0, t1)
        else:
            i0 = ui.combo_class.currentIndex()
            cg0 = start_classes[i0]
            cg1 = glist[i][:2]
            chosen = None if cg1 == cg0 else (False, cg0, cg1)
        pb_accept.setEnabled(bool(chosen))

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_change_teacher_class.ui", None, locals())
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )
    shrink()

    ## Data initialization
    suppress_events = True
    tmap = {t[0]: t[2] for t in teachers}
    glist = []
    gmap = {}
    for ci, c, gx in class_groups:
        gmap[ci] = c
        glist.append((ci, "", format_class_group(c, "")))
        glist.append(
            (ci, GROUP_ALL, format_class_group(c, GROUP_ALL))
        )
        for div in gx:
            for g in div:
                glist.append((ci, g, format_class_group(c, g)))
    # Set up comboboxes
    ui.combo_teacher.clear()
    tok = bool(start_teachers)
    if tok:
        ui.combo_teacher.addItems(tmap[ti] for ti in start_teachers)
    ui.combo_class.clear()
    gok = bool(start_classes)
    if gok:
        ui.combo_class.addItems(
            format_class_group(gmap[ci], g) for ci, g in start_classes
        )
        if not tok:
            set_teacher = False
            ui.rb_teacher.setDisabled(True)
    elif tok:
        set_teacher = True
        ui.rb_teacher.setDisabled(True)
    else:
        REPORT_INFO(T("NO_TEACHER_OR_GROUP"))
        return None
    chosen = None
    result = None
    if set_teacher:
        ui.rb_teacher.setChecked(True)
    else:
        ui.rb_class.setChecked(True)
    suppress_events = False
    on_rb_teacher_toggled(set_teacher)
    # In case a screen position was passed in:
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    tlist = [
        (1, "PQ", "Peter Quincy"),
        (7, "FT", "Fabiana Tannenhäuser"),
        (8, "SUM", "Svenja Ullmann-Meyerhof"),
        (12, "KW", "Kathrin Wollemaus"),
    ]

    _t0 = [1]

    class_groups = [
        (1, "01G", [("A", "B")],),
        (7, "05G", [("A", "B")]),
        (8, "05K", []),
        (12, "10G", [("A", "BG", "R", "G=A+BG", "B=BG+R"), ("X", "Y"),]),
    ]

    _cg0 = [(1, "B"), (8, "*"),]

    '''
    from core.db_access import get_database
    from core.classes import Classes
    from core.teachers import Teachers

    db = get_database()
    teachers = Teachers(db)
    tlist = teachers.teacher_list()
    classes = Classes(db)
    class_groups = [
        (rec.id, rec.CLASS, rec.DIVISIONS) for rec in classes.records
        if rec.id
    ]
    '''

    print("\n?teachers:")
    for t in tlist:
        print("   --", t)

    print("\n?class_groups:")
    for cg in class_groups:
        print("   --", cg)

    print("\n----->", newTeacherClassDialog(
        start_teachers = _t0,
        start_classes = _cg0,
        teachers = tlist,
        class_groups = class_groups,
        set_teacher = True,
    ))
