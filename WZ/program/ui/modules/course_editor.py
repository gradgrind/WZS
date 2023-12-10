"""
ui/modules/course_editor.py

Last updated:  2023-12-10

Edit course and blocks+lessons data.


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
T = TRANSLATIONS("ui.modules.course_editor")

### +++++

from ui.ui_base import (
    load_ui,
    ### QtWidgets:
    QWidget,
    QHeaderView,
    QAbstractButton,
    ### QtGui:
    ### QtCore:
    QObject,
    Qt,
    QEvent,
    Slot,
    ### other
    SHOW_CONFIRM,
)
from ui.course_table import CourseTable, CourseTableRow
from ui.table_support import Table

from core.base import REPORT_CRITICAL, REPORT_ERROR, REPORT_INFO
from core.db_access import db_TableRow
from core.basic_data import get_database, REPORT_SPLITTER, print_fix
from core.rooms import get_db_rooms
from core.course_base import (
    filter_activities,
    print_workload,
    workload_class,
    workload_teacher,
    text_report_field,
    grade_report_field,
    subject_print_name,
    teachers_print_names,
    block_courses,
)

#from ui.dialogs.dialog_course_fields import CourseEditorForm
from ui.dialogs.dialog_change_teacher_class import newTeacherClassDialog
from ui.dialogs.dialog_choose_timeslot import chooseTimeslotDialog
from ui.dialogs.dialog_room_choice import (
    roomChoiceDialog,
    print_room_choice,
)
from ui.dialogs.dialog_workload import workloadDialog
#from ui.dialogs.dialog_new_course_lesson import NewCourseLessonDialog
from ui.dialogs.dialog_block_name import blockNameDialog
from ui.dialogs.dialog_parallel_lessons import parallelsDialog
from ui.dialogs.dialog_text_line import textLineDialog
from ui.dialogs.dialog_integer import integerDialog
#from ui.dialogs.dialog_make_course_tables import ExportTable

def display_parallel(lesson_rec: db_TableRow) -> str:
    """Construct a display text for a parallel tag.
    """
    tag = lesson_rec.Parallel.TAG
    w = f" ({lesson_rec.Parallel.WEIGHT})" if tag else ""
    return f"{tag}{w}"

### -----


class CourseEditorPage(QObject):
    def __init__(self, parent=None):
        super().__init__()
        self.ui = load_ui("course_editor.ui", parent, self)
        self.ui.course_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.ui_table = Table(self.ui.course_table)
        self.course_table = CourseTable(self.ui_table)

        ## Set up activation for the editors for the read-only fields
        self.field_editors = {
            "wish_room": self.edit_wish_room,
            "report_title": self.edit_report_title,
            "report_teachers": self.edit_report_teachers,
            "notes": self.edit_course_notes,
            "block_name": self.edit_block_name,
            "payment": self.edit_payment,
        }
        for w in self.field_editors:
            getattr(self.ui, w).installEventFilter(self)
        ## Initialize miscellaneous variables
        self.filter_field = "CLASS"
        self.last_course: CourseTableRow = None
        self.select2index = {}

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        """Event filter for the editable fields.
        Activate the appropriate editor on mouse-left-press or return-key.
        """
        if not obj.isEnabled():
            return False
        if (event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ) or (event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Return
        ):
            try:
                h = self.field_editors[obj.objectName()]
            except KeyError:
                REPORT_CRITICAL(
                    f"Bug: No field handler for {obj.objectName()}"
                )
# Position? - obj.mapToGlobal(QPoint(0,0))
            h()
            return True
        return False
#        return super().eventFilter(obj, event)

    def enter(self):
        ## The database tables that are loaded here are expected not to
        ## change during the activity of this course-editor object.
        # Set up lists of classes, teachers and subjects for the course
        # filter. These are lists of tuples:
        #    (db-primary-key, short form, full name)
        db = get_database()
        self.db = db
        self.filter_list = {
            "CLASS": db.table("CLASSES").class_list(skip_null=False),
            "SUBJECT": db.table("SUBJECTS").subject_list(),
            "TEACHER": db.table("TEACHERS").teacher_list(skip_null=False)
        }
        self.slot_data = db.table("TT_TIME_SLOTS")
        self.all_room_lists = get_db_rooms(
            db.table("ROOMS"), db.table("TT_ROOM_GROUP_MAP")
        )
        if self.filter_field == "CLASS": pb = self.ui.pb_CLASS
        elif self.filter_field == "TEACHER": pb = self.ui.pb_TEACHER
        else: pb = self.ui.pb_SUBJECT
        pb.setChecked(True)
        self.set_combo(self.filter_field)

    ### actions

    def set_combo(self, filter_field):
        """Handle a change of filter field for the course table.
        <field> can be "CLASS", "TEACHER" or "SUBJECT".
        If a course had been selected previously, its db-primary-key
        will be in <self.last_course>.
        On the basis of this course it might be possible to select a
        particular course in the new list:
            SUBJECT: There can only be one of these – and a null value is
                     not permitted, so this is no problem.
            TEACHER: There can be more than one teacher (team teaching),
                     but mostly there will be just one. Null is possible.
                     I suggest selecting the first in the list.
            CLASS:   Similar to TEACHER, simply select the first in the list.
        """
        self.filter_field = filter_field
        combo_class = self.ui.combo_class
        if self.last_course:
            if filter_field == "CLASS":
                try:
                    g = self.last_course.group_list[0]
                    fv = g.Class.id
                except IndexError:
                    fv = None
            elif filter_field == "TEACHER":
                try:
                    t = self.last_course.teacher_list[0]
                    fv = t.Teacher.id
                except IndexError:
                    fv = None
            elif filter_field == "SUBJECT":
                fv = self.last_course.course.Subject.id
            else:
                REPORT_CRITICAL(
                    f"Bug: In <set_combo>, filter_field = '{filter_field}'"
                )
        else:
            fv = None
        # class, subject, teacher
        self.select_list = self.filter_list[filter_field]
        self.suppress_handlers = True
        combo_class.clear()
        # <self.select2index> maps the db-primary-key of a list entry
        # to its list index.
        self.select2index.clear()
        for n, kv in enumerate(self.select_list):
            combo_class.addItem(kv[2])
            self.select2index[kv[0]] = n
        combo_class.setCurrentIndex(self.select2index.get(fv, 0))
        self.suppress_handlers = False
        self.on_combo_class_currentIndexChanged(
            combo_class.currentIndex()
        )

    def load_course_table(self, select_index=-1, table_row=-1):
        """This is called to load or refresh the course list.
        <select_index> is the index of the filter selection list to be used.
        If it is not supplied (value -1), the existing filter value,
        <self.filter_value> will be used – this is useful for table
        refreshes.
        <table_row> allows a particular row to be selected initially.
        If it is not supplied (value -1), the existing row number will be
        used, if possible – this is useful for table refreshes.
        """
        # A LESSON_BLOCKS record may be shared by multiple COURSE_BASE
        # records, but only if it has a non-empty "BLOCK" field.

        if select_index >= 0:
            self.filter_value = self.select_list[select_index][0]
            #print("\n§filter_value:", self.filter_value, self.select_list)
        if table_row < 0:
            table_row = self.ui_table.current_row()

        # <filter_activities> returns a list of <COURSE_LINE> objects
        alist = filter_activities(self.filter_field, self.filter_value)
        #print("\n§course_table.load:", self.filter_field, self.filter_value)
        #print("§courses:", alist)
        _sh = self.suppress_handlers
        self.suppress_handlers = True
        self.course_table.load(alist)
        #print("§records:", self.course_table.records)
        self.course_data = None
        self.ui.pb_delete_course.setEnabled(False)
        self.ui.frame_r.setEnabled(False)
        rn = len(self.course_table.records)
        if rn > 0:
            if table_row >= rn:
                table_row = rn - 1
            self.ui.course_table.setCurrentCell(table_row, 0)
        else:
            self.ui.course_table.setCurrentCell(-1, 0)
        self.suppress_handlers = _sh
        self.on_course_table_itemSelectionChanged()
        self.total_calc()

    def display_lessons(self, lesson_block: db_TableRow):
        """Display the lesson information specified by the given
        lesson-block record.
        """
        lesson_units = self.db.table("LESSON_UNITS")
        lessons = lesson_units.get_block_units(lesson_block.id)
        self.lesson_list = lessons
        self.lesson_table = Table(self.ui.lesson_table)
        self.lesson_table.set_row_count(len(lessons))
        self.block_parallels = set()
        self.n_lessons = 0
        for row, l in enumerate(lessons):
            if l.id == 0:
                REPORT_CRITICAL("§Bug: lesson 0 used")
            # Add a lesson line
            self.lesson_table.write(row, 0, str(l.id))
            self.n_lessons += l.LENGTH
            self.lesson_table.write(row, 1, str(l.LENGTH))
            self.lesson_table.write(
                row, 2, self.slot_data.timeslot(l.Time).NAME
            )
            lpid = l.Parallel.id
            if lpid:
                if lpid in self.block_parallels:
                    REPORT_ERROR(
                        T["DOUBLE_PARALLEL"].format(tag = l.Parallel.TAG)
                    )
                    l._write("Parallel", 0) # remove the parallel tag
                else:
                    self.block_parallels.add(lpid)
            self.lesson_table.write(row, 3, display_parallel(l))
        # Disable "remove lesson" button if no lessons available
        self.ui.lesson_sub.setEnabled(self.n_lessons != 0)

    ### slots ###

    @Slot(int)
    def on_combo_class_currentIndexChanged(self, i):
        """View selection changed, reload the course table.
        The method name is a bit of a misnomer, as the selector can be
        class, teacher or subject.
        """
        if self.suppress_handlers or i < 0: return
        self.load_course_table(i, 0)

    @Slot(int, int)
    def on_lesson_table_cellActivated(self, row, col):
        #print("§on_lesson_table_cellActivated:", row, col)
        if col == 0: return
        ldata = self.lesson_list[row]
        if col == 1:
            # Edit lesson length
            l0 = ldata.LENGTH
            #print("§lesson length:", l0)
            new_length = integerDialog(
                l0,
                title = T["LESSON_LENGTH"],
                default = 1,
                min = 1,
                max = len(self.db.table("TT_PERIODS").records) - 1,
                parent = self.ui.lesson_table,
            )
            #print("§lesson length -->", ok, new_length)
            if new_length is not None and new_length != l0:
                # Change stored value
                if ldata._write("LENGTH", new_length):
                    item = self.ui.lesson_table.item(row, col)
                    item.setText(str(new_length))
                    self.n_lessons += new_length - l0
                    # Recalculate payment-field and totals
                    self.set_payment()
                    self.total_calc()
        elif col == 2:
            # Edit start time of lesson
            ts0 = ldata.Time.id
            ts = chooseTimeslotDialog(parent=self.ui.lesson_table)
            if ts is not None and ts != ts0:
                # Change stored value
                if ldata._write("Time", ts):
                    item = self.ui.lesson_table.item(row, col)
                    t = self.slot_data.timeslot(ldata.Time).NAME
                    item.setText(t)
        elif col == 3:
            # Edit parallel lessons
            lp = ldata.Parallel
            lpid0 = lp.id
            pt = parallelsDialog(lpid0, self.ui.lesson_table)
            if pt:
                lpid, tag, w = pt
                #print(f"§parallelsDialog {lpid0} -->", pt)
                item = self.ui.lesson_table.item(row, col)
                if lpid0:
                    # Modify tag parameters
                    if tag:
                        assert lpid == lpid0
                        if lp.TAG != tag:
                            assert lp._write("TAG", tag)
                        if lp.WEIGHT != w:
                            assert lp._write("WEIGHT", w)
                    else:
                        # Set reference to null.
                        assert ldata._write("Parallel", 0)
                        self.block_parallels.discard(lpid0)
                        #  If this is the last reference, remove the tag
                        if lpid > -2:
                            lp._table.delete_records([lpid0])
                elif lpid:
                    if lpid in self.block_parallels:
                        REPORT_ERROR(
                            T["DOUBLE_PARALLEL"].format(tag = tag)
                        )
                    else:
                        # Attach to existing group
                        assert ldata._write("Parallel", lpid)
                        self.block_parallels.add(lpid)
                else:
                    # New group required
                    lpid = lp._table.add_records(
                        [{"TAG": tag, "WEIGHT": w}]
                    )[0]
                    assert ldata._write("Parallel", lpid)
                    self.block_parallels.add(lpid)
                item.setText(display_parallel(ldata))

    @Slot()
    def on_lesson_add_clicked(self):
        """Add a lesson to the current lesson block.
        """
        # At present this allows the creation of a lesson even if there
        # are no teachers or pupils. That may not be terribly useful,
        # but it could be used to block a room at particular times
        # (however, there might well be better ways to do this).
        lesson_units = self.db.table("LESSON_UNITS")
        if self.lesson_list:
            l = self.lesson_list[-1].LENGTH
        else:
            l = 1
        lb = self.course_data.course.Lesson_block
        lesson_units.add_records([{
            "Lesson_block": lb.id,
            "LENGTH": l,
            "Time": 0,
            "Parallel": 0,
        }])
        self.display_lessons(lb)
        self.set_payment()
        self.total_calc()

    @Slot()
    def on_lesson_sub_clicked(self):
        """Remove a lesson from the current lesson block.
        If there are no lessons to remove, this button should be disabled
        (see method <disply_lessons>).
        """
        lesson_units = self.db.table("LESSON_UNITS")
        rec = self.lesson_list[-1]
        lesson_units.delete_records([rec.id])
        self.display_lessons(rec.Lesson_block)
        self.set_payment()
        self.total_calc()

    @Slot(QAbstractButton)
    def on_buttonGroup_buttonClicked(self, pb):
        # CLASS, SUBJECT or TEACHER
        # Note: not called when <setChecked> is called on a member button
        oname = pb.objectName()
        self.set_combo(oname.split("_", 1)[1])

    @Slot(bool)
    def on_grade_checkbox_toggled(self, on):
        """Enable/Disable grade reports for this course.
        """
        if self.suppress_handlers: return
        self.set_grade_box(on)

    @Slot(bool)
    def on_report_checkbox_toggled(self, on):
        """Enable/Disable text reports for this course.
        """
        if self.suppress_handlers: return
        if self.course_data:
            self.set_text_report_fields(REPORT_SPLITTER if on else "")

    ### field editors ###

    def edit_wish_room(self):
        assert self.course_data
        #print("$edit_wish_room +++")
        course_id = self.course_data.course.id
        rlist = self.db.table("TT_ROOMS").get_room_list(course_id)
        rxtra = self.course_data.course.Room_group
        new_rooms = roomChoiceDialog(
                start_value = ([r.Room.id for r in rlist], rxtra.id),
                classroom = self.course_data.course_line.get_classroom(),
                rooms = self.all_room_lists,
                parent = self.ui.wish_room,
#                pos = self.ui.wish_room.mapToGlobal(QPoint(0,0))
            )
        if new_rooms:
            rilist1 = new_rooms[0]
            i = 0
            to_delete = []
            for ttr in rlist:
                try:
                    ri1 = rilist1[i]
                except:
                    # Delete the record
                    to_delete.append(ttr.id)
                else:
                    # Modify the existing entry (room only), if changed
                    if (ttr.Room.id != ri1) and not ttr._write("Room", ri1):
                        REPORT_CRITICAL(
                            f"Bug: Unable to write room {ri1}"
                            " to table TT_ROOMS"
                        )
                i += 1
            if to_delete:
                self.db.table("TT_ROOMS").delete_records(to_delete)
            else:
                to_add = []
                while True:
                    try:
                        ri1 = rilist1[i]
                    except:
                        break
                    # Add a new record, SORTING = i
                    to_add.append({
                        "Course": course_id,
                        "Room": ri1,
                        "SORTING": i
                    })
                    i += 1
                if to_add:
                    self.db.table("TT_ROOMS").add_records(to_add)
            # Update room-group, if changed
            if (
                (new_rooms[1] != rxtra.id)
                and not self.course_data.course._write(
                    "Room_group", new_rooms[1])
            ):
                REPORT_CRITICAL(
                    "Bug: Validation error while writing room-group"
                    " for course"
                )
            text = print_room_choice(
                room_choice = new_rooms,
                room_lists = self.all_room_lists,
             )
            self.ui.wish_room.setText(text)

    def edit_report_title(self):
        title, sig = self.course_data.course.REPORT.split(REPORT_SPLITTER)
        new_text = textLineDialog(
            title,
            default = subject_print_name(self.course_data),
            title = T["REPORT_TITLE_LABEL"],
            parent = self.ui.report_title,
        )
        if new_text is not None:
            # Save result in REPORT field and update display
            val = f"{new_text}{REPORT_SPLITTER}{sig}"
            self.set_text_report_fields(val)

    def edit_report_teachers(self):
        title, sig = self.course_data.course.REPORT.split(REPORT_SPLITTER)
        new_text = textLineDialog(
            sig,
            default = teachers_print_names(self.course_data),
            title = T["REPORT_TEACHERS_LABEL"],
            parent = self.ui.report_teachers,
        )
        if new_text is not None:
            # Save result in REPORT field and update display
            val = f"{title}{REPORT_SPLITTER}{new_text}"
            self.set_text_report_fields(val)

    def edit_course_notes(self):
        new_text = textLineDialog(
            self.course_data.course.INFO,
            title = T["COURSE_INFO_LABEL"],
            parent = self.ui.notes,
        )
        if new_text is not None:
            # Save result in INFO field and update display
            if self.course_data.course._write("INFO", new_text):
                self.ui.notes.setText(new_text)

    def edit_block_name(self):
        lb = self.course_data.course.Lesson_block
        new_name = blockNameDialog(lb, parent = self.ui.block_name)
        #print("§edit_block_name ->", new_name)
        if new_name:
            val = str(new_name)
            if lb._write("BLOCK", val):
                self.set_block_name(val)

    def edit_payment(self):
        """There are two relevant elements:
            - field WORKLOAD in the LESSON_BLOCKS table,
            - field PAY_FACTOR in the COURSE_TEACHERS table.
        These are both text fields which are interpreted as fixed-point
        numbers.
        """
        # The "WORKLOAD" field is a text representation of a decimal number.
        # It is used in conjunction with the "PAY_FACTOR" field of the
        # associated teachers to determine a workload / payment factor for
        # the teachers.
        # If it is negative it specifies a weighting for the lessons, the
        # value is multiplied by the number of lesson periods in the block.
        # A positive "WORKLOAD" is taken as is, the number of lessons
        # playing no role. At least for "courses" (here a misnomer) with no
        # lessons, a positive value would be necessary to provide some sort
        # of workload rating.
        # There might be other cases where the number of lessons is not the
        # primary factor in determining the workload. For example, where
        # blocks of a subject are taught consecutively ("Waldorf-Epochen"),
        # it might be best to specify a weighting for an individual subject
        # block ("Epoche") as "WORKLOAD", the number of blocks being
        # specified in the "PAY_FACTOR" entries of the teachers.
        # Where the "PAY_FACTOR" is not used for a special purpose, like
        # number-of-blocks, it represents a further, personal factor. It
        # would probably mostly simply be "1", but it would allow, say, the
        # people involved in "team-teaching" to be weighted differently.
        # ambiguous.

        delta = workloadDialog(
            self.course_data,
            self.n_lessons,
            self.ui.payment
        )
        if delta:
            tlist = self.course_data.teacher_list
            for i, val in delta:
                if i < 0:
                    lb = self.course_data.course.Lesson_block
                    lb._write("WORKLOAD", print_fix(val))
                else:
                    t = tlist[i]
                    t._write("PAY_FACTOR", print_fix(val))
            self.set_payment()
            self.total_calc()

    ### supporting functions ###

    def set_grade_box(self, on: bool = None):
        """If called with no argument (<None>), the current stored value
        (GRADES field of COURSE_BASE) is to be used ("" => false).
        If necessary (and valid) set the checkbox and the current stored
        value accordingly.
        """
        state = grade_report_field(self.course_data, on)
        if state != on:
            _sh = self.suppress_handlers
            self.ui.grade_checkbox.setChecked(state)
            self.suppress_handlers = _sh

    def set_text_report_fields(self, text: str = None):
        """If the parameter is supplied, set the REPORT field to this
        value.
        Set the ui fields according to the (now) current value of this field.
        """
        on, title, sig = text_report_field(self.course_data, text)
        _sh = self.suppress_handlers
        self.suppress_handlers = True
        self.ui.report_checkbox.setChecked(on)
        self.ui.report_title.setText(title)
        self.ui.report_teachers.setText(sig)
        self.suppress_handlers = _sh

    def set_block_name(self, val):
        try:
            val0, val1 = val.split('#', 1)
            self.ui.block_name.setText(val0)
            self.ui.block_name.setToolTip(val1)
        except ValueError:
            self.ui.block_name.setText(val)
            self.ui.block_name.setToolTip("")

    def on_course_table_itemSelectionChanged(self):
        if self.suppress_handlers: return
        # Temporarily disable triggering event handling
        self.suppress_handlers = True

        row = self.ui.course_table.currentRow()
        if row >= 0:
            self.ui.pb_delete_course.setEnabled(True)
            self.course_data = self.course_table.records[row]
            self.last_course = self.course_data     # for restoring views
            self.display_lessons(self.course_data.course.Lesson_block)
            self.ui.frame_r.setEnabled(True)
        else:
            # e.g. when entering an empty table
            self.ui.frame_r.setEnabled(False)
            # Need to clear all fields
            self.lesson_table.set_row_count(0)
            self.course_data = None
            self.ui.wish_room.clear()
            self.ui.report_checkbox.setChecked(False)
            self.ui.grade_checkbox.setChecked(False)
            self.ui.report_title.clear()
            self.ui.report_teachers.clear()
            self.ui.notes.clear()
            self.set_block_name("")
            self.ui.payment.clear()
            self.suppress_handlers = False
            return

        ### Set course fields in edit panel
        #print("§course_data:", self.course_data)
        ## Room
        # The room is an ordered list of individual rooms
        # and an optional room-group.
        course_id = self.course_data.course.id
        rlist = self.db.table("TT_ROOMS").get_room_list(course_id)
        rxtra = self.course_data.course.Room_group
        #print("§get rooms:", rlist, "\n +++ ", rxtra)
        text = print_room_choice(
            room_choice = ([r.Room.id for r in rlist], rxtra.id),
            room_lists = self.all_room_lists,
         )
        self.ui.wish_room.setText(text)
        ## Now show the other course fields
        self.set_grade_box()
        # Set the text report fields
        self.set_text_report_fields()
        # Reenable event handlers
        self.suppress_handlers = False
        # The course info text:
        self.ui.notes.setText(self.course_data.course.INFO)
        self.set_block_name(self.course_data.course.Lesson_block.BLOCK)
        self.set_payment()

    def set_payment(self):
        """The payment field has two elements, the WORKLOAD value and the
        PAY_FACTOR value for each involved teacher.
        WORKLOAD can be negative, then it is a weight for the number of
        lessons. The final pay-factor is the workload multiplied by the
        teacher's PAY_FACTOR. If all teachers have the same value, a
        general value can be shown, otherwise each teacher must be shown
        with their own personal value.
        """
        self.ui.payment.setText(
            print_workload(
                self.course_data.course.Lesson_block.WORKLOAD,
                self.n_lessons,
                [
                    (ct.Teacher.TID, ct.PAY_FACTOR)
                    for ct in self.course_data.teacher_list
                ]
            )
        )

    @Slot(int,int)
    def on_course_table_cellActivated(self, row, col):
        #print("§on_course_table_cellActivated:", row, col)
        #print("   ...", self.course_data)
        if col > 0:
            if self.course_table.edit_cell(row, col):
                self.load_course_table()

    @Slot()
    def on_pb_change_all_clicked(self):
        """All records in the table with a particular teacher or
        class-group will have this field substituted.
        """
        if not self.course_data:
            REPORT_INFO(T["NO_COURSE"])
            return
        tlist = self.db.table("TEACHERS").teacher_list()
        classes = self.db.table("CLASSES")
        class_groups = [
            (rec.id, rec.CLASS, rec.DIVISIONS) for rec in classes.records
            if rec.id
        ]
        t0 = [t.Teacher.id for t in self.course_data.teacher_list]
        cg0 = [(g.Class.id, g.GROUP_TAG) for g in self.course_data.group_list]
        changes = newTeacherClassDialog(
            start_teachers = t0,
            start_classes = cg0,
            teachers = tlist,
            class_groups = class_groups,
            set_teacher = self.filter_field != "TEACHER",
            parent = self.ui.course_table,
        )
        if changes:
            print("§on_pb_change_all_clicked:", changes)
            tset, old, new = changes
            # Search all courses in the table for this item ...
            if tset:
                for cdata in self.course_table.records:
                    print("   --", cdata)   # COURSE_LINEs
                    for t in cdata.teacher_list:
                        if t.Teacher.id == old:
                            t._write("Teacher", new)
                t._table.clear_caches()
            else:
                id0, g0 = old
                id1, g1 = new
                for cdata in self.course_table.records:
                    print("   --", cdata)   # COURSE_LINEs
                    for g in cdata.group_list:
                        if g.Class.id == id0 and g.GROUP_TAG == g0:
                            fmap = {}
                            if id1 != id0:
                                fmap["Class"] = id1
                            if g1 != g0:
                                fmap["GROUP_TAG"] = g1
                            if fmap:
                                g._table.update_cells(g.id, **fmap)
                g._table.clear_caches()
            self.load_course_table()

    @Slot()
    def on_pb_new_course_clicked(self):
        """Add a new course.
        The fields of the current course, if there is one, will be taken
        as "template".
        """
        block = blockNameDialog()
        #print("§block:", repr(block))
        #print("§new_course:", self.course_data)
        course = self.course_data.course._todict()
        #print("§course:", course)
        glist = [
            {"Class": g.Class.id, "GROUP_TAG": g.GROUP_TAG}
            for g in self.course_data.group_list
        ]
        #print("§groups:", glist)
        tlist = [
            {"Teacher": t.Teacher.id, "PAY_FACTOR": print_fix(t.PAY_FACTOR)}
            for t in self.course_data.teacher_list
        ]
        #print("§teachers:", tlist)
        if block.id is None:
            # New block => new record in LESSON_BLOCKS
            lbtable = self.db.table("LESSON_BLOCKS")
            lbid = lbtable.add_records([{
                "BLOCK": str(block),
                "WORKLOAD": "-1",
                "NOTES": ""
            }])[0]
        else:
            # Add to existing block
            lbid = block.id
        cbtable = self.db.table("COURSE_BASE")
        cbid = cbtable.add_records([{
            "Subject": course["Subject"],
            "Lesson_block": lbid,
            "Room_group": course["Room_group"],
            "REPORT": "",
            "GRADES": "",
            "INFO": "",
        }])[0]
        # Copy over teacher(s) and group(s), new entries are be needed in
        # the associated tables.
        to_add = []
        for g in glist:
            g["Course"] = cbid
            to_add.append(g)
        self.db.table("COURSE_GROUPS").add_records(to_add)
        to_add.clear()
        for t in tlist:
            t["Course"] = cbid
            to_add.append(t)
#TODO: entries in TT_ROOMS?
        self.db.table("COURSE_TEACHERS").add_records(to_add)
        self.load_course_table()

    @Slot()
    def on_pb_delete_course_clicked(self):
        """Delete the current course.
        This can have knock-on effects in tables LESSON_BLOCKS, LESSON_UNITS,
        COURSE_GROUPS, COURSE_LESSONS and TT_ROOMS
        """
        row = self.ui_table.current_row()
        assert row >= 0, "No course, delete button should be disabled"
        if not SHOW_CONFIRM(T["REALLY_DELETE"]):
            return
        # If there are no other courses using the LESSON_BLOCKS record,
        # that must be deleted, which would mean the LESSON_UNITS records
        # referring to it must also be deleted.
        # Also, all records in COURSE_GROUPS, COURSE_LESSONS and TT_ROOMS
        # referring to the course must be deleted before the COURSE_BASE
        # record itself can be deleted.
        course = self.course_data.course
        cbid = course.id
        lbid = course.Lesson_block.id
        glist = [g.id for g in self.course_data.group_list]
        #print("§groups:", glist)
        tlist = [t.id for t in self.course_data.teacher_list]
        #print("§teachers:", tlist)
        tt_rooms = self.db.table("TT_ROOMS")
        rlist = [r.id for r in tt_rooms.get_room_list(cbid)]
        #print("§rooms:", rlist)
        block = course.Lesson_block.BLOCK
        # Remove the groups, teachers and rooms
        self.db.table("COURSE_GROUPS").delete_records(glist)
        self.db.table("COURSE_TEACHERS").delete_records(tlist)
        tt_rooms.delete_records(rlist)
        # Remove the course record
        self.db.table("COURSE_BASE").delete_records([cbid])
        ## This must be last, after the course-base record is gone
        # Other associated courses?
        if lbid and ((not block) or (not block_courses(lbid))):
            ## Delete lesson block and lessons
            # Get lessons, remove their records from LESSON_UNITS
            llist = [l.id for l in self.lesson_list]
            self.db.table("LESSON_UNITS").delete_records(llist)
            # Remove the LESSON_BLOCKS record
            self.db.table("LESSON_BLOCKS").delete_records([lbid])
        self.load_course_table()

    def total_calc(self):
        """For teachers and classes determine the total workload.
        For classes, the (sub-)groups will be taken into consideration, so
        that groups with differing total will be shown.
        """
        if self.filter_field == "CLASS":
            if self.filter_value == 0:
                self.ui.total.clear()
                self.ui.total.setEnabled(False)
            else:
                g_n_list = workload_class(
                    self.filter_value, self.course_table.records
                )
                text = " ;  ".join((f"{g}: {n}") for g, n in g_n_list)
                self.ui.total.setText(text)
                self.ui.total.setEnabled(True)
        elif self.filter_field == "TEACHER":
            if self.filter_value == 0:
                self.ui.total.clear()
                self.ui.total.setEnabled(False)
            else:
                nlessons, total = workload_teacher(
                    self.filter_value, self.course_table.records
                )
                self.ui.total.setText(T["TEACHER_TOTAL"].format(
                    n=nlessons, total=print_fix(total)
                ))
            self.ui.total.setEnabled(True)
        else:
            self.ui.total.clear()
            self.ui.total.setEnabled(False)

#TODO
    @Slot()
    def on_make_tables_clicked(self):
        ExportTable(parent=self).activate()


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from ui.ui_base import run

    widget = CourseEditorPage()
    widget.enter()
    widget.ui.resize(1000, 550)
    run(widget.ui)
