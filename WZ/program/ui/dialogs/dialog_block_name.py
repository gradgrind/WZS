"""
ui/dialogs/dialog_block_name.py

Last updated:  2023-12-16

Supporting "dialog" for the course editor – choose or edit the name tag
for a lesson block.


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

from core.base import TRANSLATIONS
T = TRANSLATIONS("ui.dialogs.dialog_block_name")

### +++++

from typing import Optional
import re

from core.base import REPORT_CRITICAL
from core.db_access import db_TableRow
from core.basic_data import get_database
from core.course_base import (
    BLOCK_short,
    BLOCK_subject,
    BLOCK_tag,
    BLOCK,
    blocks_info,
    block_courses,
)

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

#TODO: What about a "reset" button, visible only when a named block can
# be "de-named", i.e. when there is only a single attached course?

def blockNameDialog(
    start_value: Optional[db_TableRow] = None,  # a BLOCK_LESSONS row
    parent: Optional[QWidget] = None,
) -> Optional[str]:

    new_block = None
    result = None

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = new_block

    @Slot()
    def reset():
        nonlocal new_block
        new_block = BLOCK()
        ui.accept()

    @Slot(str)
    def on_block_select_currentTextChanged(block_key):
        if suppress_handlers: return
        #print("§on_block_select_currentTextChanged:", block_key)
        if block_key:
            # Fill all fields according to the block
            block = block_map[block_key]
            ui.subject.setText(block.subject)
            ui.block_sid.setText(block.short)
            ui.block_tag.setText(block.tag)
            ui.notes.setText(block.notes)
        else:
            # Clear all fields ...
            ui.subject.clear()
            ui.block_sid.clear()
            ui.block_tag.clear()
            ui.notes.clear()
        check_acceptable()

    @Slot(str)
    def on_block_tag_textEdited(t):
        check_acceptable()

    @Slot(str)
    def on_block_sid_textEdited(t):
        check_acceptable()

    @Slot(str)
    def on_subject_textEdited(t):
        check_acceptable()

    @Slot(str)
    def on_notes_textEdited(t):
        check_acceptable()

    ##### functions #####

    def shrink():
        ui.resize(0, 0)

    def show_course_info(lb_id: int):
        """Display the course(s) and the lesson list associated with the
        given lesson-block-id.
        """
        ui.course_list.clear()
        if lb_id:
            for b in block_courses(lb_id):
                ui.course_list.addItem(str(b))
            # Show the associated lessons
            db = get_database()
            llist = []
            for l in db.table("LESSON_UNITS").get_block_units(lb_id):
                t = l.Time
                if t.id:
                    llist.append(f"{l.LENGTH}({t._table.timeslot(t).NAME})")
                else:
                    llist.append(str(l.LENGTH))
            ui.lesson_list.setText(", ".join(llist))
        else:
            ui.lesson_list.clear()

    def check_acceptable():
        nonlocal new_block
        # Test if current settings are valid and "acceptable".
        # One aspect is whether the name ("key" – only use subject-tag
        # and block-tag for the comparison) is already in use.
        bt = ui.block_tag.text()
        bs = ui.block_sid.text()
        s = ui.subject.text()
        c = ui.notes.text()
        status = ""
        new_block = None
        if s:
            if not re.match(f"^{BLOCK_short}$", bs):
                status = T["BAD_SHORT"]
            elif not re.match(f"^{BLOCK_subject}$", s):
                status = T["BAD_SUBJECT"]
            elif bt and not re.match(f"^{BLOCK_tag}$", bt):
                status = T["BAD_TAG"]
            else:
                block = BLOCK(
                    subject = s,
                    tag = bt or None,
                    short = bs,
                    notes = c or None,
                )
                key = block.key()
                try:
                    lbx = block_map[key]
                except KeyError:
                    # This is a new block-name
                    if start_value is None:
                        # Clear course/lessons
                        show_course_info(0)
                    new_block = block
                else:
                    if start_value is None:
                        if (
                            lbx.short != block.short
                            or lbx.notes != block.notes
                        ):
                            status = T["KEY_FOUND_MISMATCH"].format(key = key)
                        else:
                            new_block = lbx
                            show_course_info(lbx.id)
                    else:
                        status = T["BLOCK_EXISTS"].format(key = key)
        elif bt or bs or c:
            status = T["NO_SUBJECT"]
        elif start_value is None:
            show_course_info(0)
            new_block = BLOCK()
        else:
            # No subject, i.e. not a block, but more than one course
            if key0:
                status = T["EMPTY_NOT_POSSIBLE"]
            else:
                status = T["ALREADY_EMPTY"]
        if status:
            ui.status.setStyleSheet(
                "background-color: rgb(249, 240, 180); "
                "color: rgb(204, 0, 0);"
            )
            ui.status.setText(status)
        else:
            colour = "(0, 0, 180)" if new_block.id else "(0, 180, 0)"
            ui.status.setStyleSheet(
                "background-color: rgb(249, 240, 180); "
                f"color: rgb{colour};"
            )
            ui.status.setText(str(new_block))
        pb_accept.setDisabled(bool(status))

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_block_name.ui", None, locals())
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )
    pb_reset = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Reset
    )
    pb_reset.clicked.connect(reset)
    shrink() # minimize dialog window

    ## Data initialization
    block_map = blocks_info()
    suppress_handlers = True
    # Set up block selector combobox
    ui.block_select.clear()
    ui.block_select.addItem("")
    ui.block_select.addItems(sorted(block_map))
    if start_value is None:
        # A new lesson-block is to be created. It can be a simple one (no
        # block-name) or it can have a new block-name.
        # In this case there is also the possibility of joining an existing
        # block.
        key0 = 0
        pb_reset.hide()
    else:
        # An existing lesson-block has been supplied.
        # The name of the block may be changed.
        # The new name (key) must not be in use currently.
        # If there is only one course using this block, it is also possible
        # to return a null-block, so that the course becomes a non-block one.
        lb_id = start_value.id
        block0 = (
            BLOCK.read(start_value.BLOCK, id = lb_id)
            or BLOCK(id = lb_id)
        )
        courses = block_courses(lb_id)    # -> list[COURSE_LINE]
        if not courses:
            REPORT_CRITICAL(
                f"Bug in '{__name__}': LESSON_BLOCKS record"
                f" (id = {start_value.id}) has no associated course"
            )
        key0 = block0.key()
        pb_reset.setVisible(len(courses) == 1 and bool(key0))

        # Set the initial block choice
        ui.block_select.setCurrentText(key0)
        ui.block_select.setEnabled(False)
        show_course_info(lb_id)
    suppress_handlers = False
    on_block_select_currentTextChanged(key0)

    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    result = None
    #widget.setFocus()
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

# It is difficult to test this module without using the associated
# database tables. These would have to be simulated somehow.
if __name__ == "__main__":
    print("\n??? None")
    print("----->", repr(blockNameDialog()))
    db = get_database()
    lb = db.table("LESSON_BLOCKS")
    for rec in lb.records:
        if rec.id and not rec.BLOCK:
            print("\n??? 0:", rec)
            print("----->", repr(blockNameDialog(rec)))
            break
    for rec in lb.records:
        if rec.BLOCK:
            if len(block_courses(rec.id)) == 1:
                print("\n??? 1:", rec)
                print("--1-->", repr(blockNameDialog(rec)))
                break
    for rec in lb.records:
        if rec.BLOCK:
            if len(block_courses(rec.id)) > 1:
                print("\n??? >1:", rec)
                print("- >1->", repr(blockNameDialog(rec)))
                break
