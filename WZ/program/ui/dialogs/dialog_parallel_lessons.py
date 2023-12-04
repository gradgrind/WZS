"""
ui/dialogs/dialog_parallel_lessons.py

Last updated:  2023-12-04

Supporting "dialog" for the course editor – mark lessons which should
start at the same time.


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
T = TRANSLATIONS("ui.dialogs.dialog_parallel_lessons")

### +++++

from typing import Optional

from core.base import REPORT_CRITICAL
from core.basic_data import get_database
from core.course_base import ParallelTags, block_courses, db_TableRow
from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    ### QtGui:
    QRegularExpressionValidator,
    ### QtCore:
    Slot,
    QRegularExpression,
    ### other
    load_ui,
)

### -----

#TODO: Might want to be able to clear out unused parallel tags here, or
# somewhere on a housekeeping page. When the last reference to an entry
# is removed, the entry is removed automatically (in "course_editor"), so
# it is not clear that such a feature would really be needed.

def parallelsDialog(
    start_value: int = 0,   # rowid for PARALLEL_TAGS table
    parent: Optional[QWidget] = None,
) -> Optional[tuple[int, str, str]]:
    """Edit an existing parallel-tag, remove it from a lesson, or create
    a new record in the PARALLEL_TAGS table.
    Return a tuple if any change is to be made:
        - id of PARALLEL_TAGS record, 0 if a new one is required
        - TAG field
        - WEIGHT field

    To edit an existing parallel-tag, its index will be passed as
    <start_value>. Any of the fields can be changed, but not to another
    existing TAG.
    There is also a "reset" button which will cause the tag to be removed
    from the lesson it was fetched from. In this case, the return value is
    (0, "", "-").
    As a special case, when <start_value> is null (0), it is possible to
    return an existing TAG. No changes to the tag are possible.
    """

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = value

    @Slot()
    def reset():
        nonlocal value
        value = (-len(courses0), "", "-")
        ui.accept()

    @Slot(str)
    def on_category_currentTextChanged(value: str):
        nonlocal suppress_events
        if suppress_events: return
        suppress_events = True
        populate_tags(value)
        # Clear "tag" field
        ui.tag.setEditText("")
        suppress_events = False
        value_changed()

    @Slot(str)
    def on_tag_currentTextChanged(value: str):
        if suppress_events: return
        # If this corresponds to a known TAG, set the weight
        tag, pt = known_tag(ui.category.currentText(), value)
        if pt:
            ui.weight.setCurrentText(pt.WEIGHT)
        value_changed()

    @Slot(str)
    def on_weight_currentTextChanged(value: str):
        if suppress_events: return
        value_changed()

    ##### functions #####

    def shrink():
        ui.resize(0, 0)

    def value_changed():
        nonlocal value
        tag, pt = known_tag(
            ui.category.currentText(),
            ui.tag.currentText()
        )
        ui.lesson_list.clear()
        accept_ok = True
        wchange_ok = True
        if tag:
            if pt is None:
                # The value is not currently in use.
                # This can be used as a "new" value, if <start_value> is 0,
                # or else to modify an existing entry.
                id = start_value
            else:
                ptid = pt.id
                if start_value:
                    id = start_value
                    if ptid != start_value:
                        # Not acceptable, can only change the current tag
                        accept_ok = False
                else:
                    # Join an existing parallel group
                    id = ptid
                    wchange_ok = False
                lunits = [
                    l for l in lesson_units.records
                    if l.Parallel.id == ptid
                ]
                courses.clear()
                for lunit in lunits:
                    lb = lunit.Lesson_block
                    if lb.BLOCK:
                        course = f"[{lb.BLOCK}]"
                    else:
                        clist = block_courses(lb.id)
                        assert len(clist) == 1
                        course = str(clist[0])
                    if course in courses:
                        REPORT_CRITICAL(
                            f"Bug: course {course} parallel to itself"
                        )
                    lt = lunit.Time
                    ltn = f" @ {lt._table.timeslot(lt).NAME}" if lt.id else ""
                    courses[course] = f"{lunit.LENGTH}{ltn}  ( {lunit.id} )"
                ui.lesson_list.addItems(
                    f"{c} || {ldata}" for c, ldata in courses.items()
                )
            w = ui.weight.currentText()
            if tag == value0 and w == w0:
                # unchanged
                accept_ok = False
            #print("§???:", tag, value0, w, w0)
            value = (id, tag, w)
        else:
            accept_ok = False
            value = None
        pb_accept.setEnabled(accept_ok)
        ui.weight.setEnabled(wchange_ok)
        #print("§value_changed:", value, accept_ok)

    def category_map(cat):
        """Return a list of tags for the given category.
        """
        return ptags.tag_maps()[1].get(cat) or []

    def populate_categories(cat, tag):
        cmap = ptags.tag_maps()[1]
        ui.category.clear()
        ui.category.addItems(sorted(cmap))
        icat = ui.category.findText(cat)
        if icat < 0:
            REPORT_CRITICAL(
                "Bug in dialog_parallel_lessons::populate_categories"
                f' Invalid "category" ({cat})'
            )
        ui.category.setCurrentText(cat)
        populate_tags(cat)
        itag = ui.tag.findText(tag)
        if itag < 0:
            REPORT_CRITICAL(
                "Bug in dialog_parallel_lessons::populate_categories"
                f' Invalid "tag" ({tag})'
            )
        ui.tag.setCurrentIndex(itag)

    def populate_tags(cat):
        taglist = category_map(cat)
        ui.tag.clear()
        ui.tag.addItems(sorted(taglist))

    def known_tag(cat: str, tag: str) -> Optional[db_TableRow]:
        """Return a tuple:
            - the tag constructed from the two given parts
            - the PARALLEL_TAGS record with the given tag, if there
              is one, otherwise <None>.
        """
        if cat or tag:
            t1 = f"{cat}~" if cat else ""
            t = f"{t1}{tag}"
            return (t, ptags.tag_maps()[0].get(t))
        return ("", None)

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_parallel_lessons.ui", None, locals())
    suppress_events = True
    pb_reset = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Reset
    )
    if start_value:
        pb_reset.clicked.connect(reset)
        pb_reset.show()
    else:
        pb_reset.hide()
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )
    rx = QRegularExpression(r"[\w._/-]*")
    validator = QRegularExpressionValidator(rx, ui)
    ui.category.setValidator(validator)
    ui.tag.setValidator(validator)

    ## Data initialization

    db = get_database()
    ptags = db.table("PARALLEL_TAGS")
    lesson_units = db.table("LESSON_UNITS")
    courses = {}
    __category_map = {}
    ptag0 = ptags[start_value]
    value0 = ptag0.TAG
    w0 = ptag0.WEIGHT
    populate_categories(*ParallelTags.split_tag(ptag0))
    ui.weight.setCurrentText(w0)
    value = None
    result = None
    new_entry = False
    value_changed()
#TODO?
    courses0 = list(courses)    # or set?

    ## Activate the dialog
    shrink()
    suppress_events = False
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    #ui.textline.setFocus()
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    print("----->", parallelsDialog(1))
    print("----->", parallelsDialog(0))
