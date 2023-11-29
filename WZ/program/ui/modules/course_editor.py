"""
ui/modules/course_editor.py

Last updated:  2023-11-27

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
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractButton,
    QInputDialog,
    ### QtGui:
#    QIcon,
    ### QtCore:
    QObject,
    Qt,
#    QPoint,
    QEvent,
    Slot,
)
from ui.course_table import CourseTable, CourseTableRow

from core.base import REPORT_CRITICAL
from core.db_access import db_TableRow
from core.basic_data import get_database, REPORT_SPLITTER
#from core.classes import Classes
#from core.teachers import Teachers
#from core.subjects import Subjects
#from core.time_slots import TimeSlots
from core.rooms import get_db_rooms
from core.course_base import (
    filter_activities,
    get_pay_value,
    workload_class,
    workload_teacher,
    text_report_field,
    grade_report_field,
    subject_print_name,
    teachers_print_names,
    blocks_info,
#    course_rooms,
#    update_course_rooms,
#    COURSE_INFO,
#    get_lesson_list,
#    get_teacher_pay_value,
#    read_room_list,
#    lesson_pay_display,
)

#from ui.dialogs.dialog_course_fields import CourseEditorForm
#from ui.dialogs.dialog_courses_field_mod import FieldChangeForm
#from ui.dialogs.dialog_choose_timeslot import chooseTimeslotDialog
from ui.dialogs.dialog_room_choice import (
    roomChoiceDialog,
    print_room_choice,
)
#from ui.dialogs.dialog_workload import WorkloadDialog
#from ui.dialogs.dialog_new_course_lesson import NewCourseLessonDialog
from ui.dialogs.dialog_block_name import blockNameDialog
#from ui.dialogs.dialog_parallel_lessons import ParallelsDialog
from ui.dialogs.dialog_text_line import textLineDialog
#from ui.dialogs.dialog_make_course_tables import ExportTable

### -----


class Table:
    """A wrapper around a QTableWidget to encapsulate the interface
    needed in the course editor.
    """
    def __init__(self,
        qtablewidget: QTableWidget,
        centre: set[int] = None,
    ):
        self.qtable = qtablewidget
        self.align_centre = centre or set()

    def set_row_count(self, n):
        n0 = self.qtable.rowCount()
        if n > n0:
            self.qtable.setRowCount(n)
            nc = self.qtable.columnCount()
            for r in range(n0, n):
                for c in range(nc):
                    item = QTableWidgetItem()
                    if c in self.align_centre:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.qtable.setItem(r, c, item)
        elif n < n0:
            self.qtable.setRowCount(n)

    def write(self, row: int, column: int, text: str):
        self.qtable.item(row, column).setText(text)

    def current_row(self):
        return self.qtable.currentRow()


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
                    f"TODO: No field handler for {obj.objectName()}"
                )
# Position? - obj.mapToGlobal(QPoint(0,0))
            h()
            return True
#TODO: Shouldn't "return False" be good enough here?
        return False
        return super().eventFilter(obj, event)

    def enter(self):
        ## The database tables that are loaded here are expected not to
        ## change during the activity of this course-editor object.
        # Set up lists of classes, teachers and subjects for the course
        # filter. These are lists of tuples:
        #    (db-primary-key, short form, full name)
#TODO: Also need mapping TID -> Signature?
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

#?
        self.course_field_changer = None

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

    def load_course_table(self, select_index=-1, table_row=-1, lesson_id=-1):
        """This is called to load or refresh the course list.
        """
#TODO: Describe parameters.
#TODO: Is refreshing still required?
#TODO: Is <self.lesson_restore_id> still required? Possibly not, as the
# lesson line is not used anywhere any more (I think).
#        self.lesson_restore_id = lesson_id

# A "workload/payment only" type is only distinguished by having no
# lesson-unit entries associated with it. So perhaps there is actually
# only the question of a block name, which would enable multiple "courses"
# to share the lesson-block entry.
# The WORKLOAD field is, however, a bit complicated and perhaps a little
# ambiguous. It can simply contain the "value" of the block as a number
# of work-hour ("Deputatsstunden") equivalents. This might be helpful for
# entries with no actual lessons.
# Where there are lessons, it might be more helpful to have a weighting
# factor for the number of lessons. But where there are blocks taught
# consecutively ("Epochen"), it might be more helpful to specify a
# weighting for an individual block, the number of blocks being specified
# in the "course-teachers" entries.

        if select_index >= 0:
            self.filter_value = self.select_list[select_index][0]
            #print("\n§filter_value:", self.filter_value, self.select_list)
#TODO: This may have been connected with refreshing, in which case it might
# be superfluous now.
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
#        self.ui.pb_edit_course.setEnabled(False)
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
#        self.lesson_restore_id = -1
        self.total_calc()

    def display_lessons(self, lesson_block: db_TableRow):
        """Display the lesson information specified by the given
        lesson-block record.
        """
        lesson_units = self.db.table("LESSON_UNITS")
        lessons = lesson_units.get_block_units(lesson_block.id)
        self.lesson_table = Table(self.ui.lesson_table)
        self.lesson_table.set_row_count(len(lessons))
#TODO: Is the number of lessons really needed (for the workload/payment)?
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
            self.lesson_table.write(row, 3, l.Parallel.TAG)

    ### slots ###

    @Slot(int)
    def on_combo_class_currentIndexChanged(self, i):
        """View selection changed, reload the course table.
        The method name is a bit of a misnomer, as the selector can be
        class, teacher or subject.
        """
        if self.suppress_handlers or i < 0: return
        self.load_course_table(i, 0)

#    @Slot(int, int)
#    def on_lesson_table_cellClicked(self, row, col):
#        print("§on_lesson_table_cellClicked:", row, col)

    @Slot(int, int)
    def on_lesson_table_cellActivated(self, row, col):
        #print("§on_lesson_table_cellActivated:", row, col)
        #if col == 0: return
        ldata = self.lesson_lists[self.course_data["Lesson_block_id"]]
        llist = ldata[1]
        if col == 1:
            # Edit lesson length
            lrow = llist[row]
            l0 = lrow["LENGTH"]
            #print("§lesson length:", l0)
            new_length, ok = QInputDialog.getInt(
                self.ui.lesson_table,
                T["LESSON_LENGTH"],
                T["LESSON_PERIODS"],
                value = l0,
                minValue = 1,
                # Use periods-per-day as maximum value
                maxValue = len(self.slot_data.period_map) - 1
                #step = 1,
                #flags = Qt::WindowFlags()
            )
            #print("§lesson length -->", ok, new_length)
            if new_length != l0:
                # Change stored value
                #print("§lesson length =", new_length)
                #print("§llist[row]:", lrow)
                db_query(
                    "update LESSON_UNITS set LENGTH=? where Lesson_unit_id=?",
                    (new_length, lrow["Lesson_unit_id"])
                )
                db_commit()
                lrow["LENGTH"] = new_length
                self.ui.lesson_table.item(row, col).setText(str(new_length))
                self.n_lessons += new_length - l0
                ldata[0] = self.n_lessons
                # Recalculate payment-field and totals
                self.set_payment()
                self.total_calc()

        elif col == 2:
            # Edit start time of lesson
            ts = chooseTimeslotDialog(parent=self.ui.lesson_table)
            if ts is not None:
                # Change stored value
                lrow = llist[row]
                #print("§llist[row]:", ts, lrow)
                if ts != lrow["TIME"]:
                    db_query(
                        "update LESSON_UNITS set TIME=? where Lesson_unit_id=?",
                        (ts, lrow["Lesson_unit_id"])
                    )
                    db_commit()
                    lrow["TIME"] = ts
                    text = TimeSlots.read().timeslots[ts].NAME
                    self.ui.lesson_table.item(row, col).setText(text)

        elif col == 3:
            # Edit parallel lessons
            assert False, "TODO: Edit parallel lessons"

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

#    @Slot()
#    def on_lesson_table_itemSelectionChanged(self):
#        print("§on_lesson_table_itemSelectionChanged:",
#            self.ui.lesson_table.currentRow(),
#            self.ui.lesson_table.currentColumn(),
#        )
#        return

    ### field editors ###

    def edit_wish_room(self):
        assert self.course_data
        #print("$edit_wish_room +++")
        course_id = self.course_data.course.id
        rlist = self.db.table("TT_ROOMS").get_room_list(course_id)
        rxtra = self.course_data.course.Room_group
        new_rooms = roomChoiceDialog(
                start_value = ([r.id for r in rlist], rxtra.id),
                classroom = self.course_data.course_line.get_classroom(),
                rooms = self.all_room_lists,
                parent = self.ui,
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
            parent = self.ui,
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
            parent = self.ui,
        )
        if new_text is not None:
            # Save result in REPORT field and update display
            val = f"{title}{REPORT_SPLITTER}{new_text}"
            self.set_text_report_fields(val)

    def edit_course_notes(self):
        new_text = textLineDialog(
            self.course_data.course.INFO,
            title = T["COURSE_INFO_LABEL"],
            parent = self.ui,
        )
        if new_text is not None:
            # Save result in INFO field and update display
            self.course_data.course._write("INFO", new_text)
            self.ui.notes.setText(new_text)

    def edit_block_name(self):
        lb = self.course_data.course.Lesson_block
        new_name = blockNameDialog(lb, blocks_info())
        print("§edit_block_name ->", new_name)
        #self.ui.block_name

        return

        if block.id == 0:
            # Any block name which isn't already in use can be entered.
            # Of course, I need a set/map of existing block names to
            # check this.
            regex = r"^(\w+):([^*]+)(?:\*(\w+))(?:#(.*))$"
            re.match(
                regex, "HU:Hauptunterricht*OS#Für die Oberstufe"
            ).groups()
            # The comment as tooltip?

            #block_courses(block_id: int) -> list[COURSE_LINE]



    def edit_payment(self):
        assert False, "TODO: edit_payment"

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

    def on_course_table_itemSelectionChanged(self):
        if self.suppress_handlers: return
        # Temporarily disable triggering event handling
        self.suppress_handlers = True

        row = self.ui.course_table.currentRow()
#TODO--
        print(f"\n§on_course_table_itemSelectionChanged: TODO {row}")
#        return

#        lesson_id = self.lesson_restore_id
        if row >= 0:
            self.ui.pb_delete_course.setEnabled(True)
#? Perhaps I only want add and delete for course rows?
#            self.ui.pb_edit_course.setEnabled(True)

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
            self.ui.block_name.clear()
            self.ui.payment.clear()
            self.suppress_handlers = False
            return

        ### Set course fields in edit panel
        print("§course_data:", self.course_data)
        ## Room
        # The room is an ordered list of individual rooms
        # and an optional room-group.
        course_id = self.course_data.course.id
        rlist = self.db.table("TT_ROOMS").get_room_list(course_id)
        rxtra = self.course_data.course.Room_group
        #print("§get rooms:", rlist, "\n +++ ", rxtra)
        text = print_room_choice(
            room_choice = ([r.id for r in rlist], rxtra.id),
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
        self.ui.block_name.setText(
            self.course_data.course.Lesson_block.BLOCK
        )
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
            get_pay_value(self.course_data, self.n_lessons)
        )

    @Slot(int,int)
    def on_course_table_cellDoubleClicked(self, r, c):
        self.edit_course(r)

    @Slot()
    def on_pb_edit_course_clicked(self):
        self.edit_course(self.ui_table.current_row())

    @Slot()
    def on_pb_change_all_clicked(self):
        """Either all teacher fields or all class fields for the current
        teacher+class are to be changed to a new value.
        """
        if not self.course_data:
            return
        if not self.course_field_changer:
            # Initialize dialog
            self.course_field_changer = FieldChangeForm(
                self.filter_list, self
            )
        changes = self.course_field_changer.activate(
            self.course_data, self.filter_field
        )
        if changes:
            cid, tid, field, newval = changes
            chlist = []
            for cdatalist in self.course_list:
                cdata = cdatalist[0]
                if cdata["CLASS"] == cid and cdata["TEACHER"] == tid:
                    chlist.append(cdata["Course"])
            for course in chlist:
                #print("CHANGE", field, newval, course)
                db_update_field("COURSES", field, newval, course=course)
            self.load_course_table(
                self.combo_class.currentIndex(),
                self.ui_table.current_row()
            )

    def edit_course(self, row):
        """Activate the course field editor."""
        changes = self.edit_course_fields(self.course_data)
        if changes:
            self.update_course(row, changes)

    def update_course(self, row, changes):
        if db_update_fields(
            "COURSES",
            [(f, v) for f, v in changes.items()],
            course=self.course_id,
        ):
            self.load_course_table(self.combo_class.currentIndex(), row)
        else:
            raise Bug(f"Course update ({self.course_id}) failed: {changes}")

    @Slot()
    def on_pb_new_course_clicked(self):
        """Add a new course.
        The fields of the current course, if there is one, will be taken
        as "template".
        """
#TODO
        print("§new_course:", self.course_data)

#TODO
    @Slot()
    def on_pb_delete_course_clicked(self):
        """Delete the current course."""
        row = self.ui_table.current_row()
        assert row >= 0, "No course, delete button should be disabled"
        if not SHOW_CONFIRM(T["REALLY_DELETE"]):
            return
        # Delete each connected entry in COURSE_LESSONS, keeping track
        # of the lesson-groups and lesson-datas.

#?
#    @Slot()
#    def _on_lesson_table_itemSelectionChanged(self):
#        print("§on_lesson_table_itemSelectionChanged:",
#            self.ui.lesson_table.currentRow(),
#            self.ui.lesson_table.currentColumn(),
#        )

    def field_editor(self, obj: QLineEdit):
        object_name = obj.objectName()
        lthis = self.current_lesson[1] # the Record object
        lid = lthis["Lid"]
        ### PAYMENT (LESSON_DATA)
        if object_name == "payment":
            result = WorkloadDialog.popup(
                start_value=lthis, parent=self
            )
            if result is not None:
                # Update the db. A redisplay is only necessary because
                # all loaded "activities" with the same pay data must
                # be updated.
                db_update_fields(
                    "LESSON_DATA",
                    (   ("Pay_factor_id", result[1]),
                        ("PAY_NLESSONS", result[0])
                    ),
                    Lesson_data=lthis["Lesson_data"]
                )
                self.load_course_table(lesson_id=lid)
        ### ROOM (LESSON_DATA)
        elif object_name == "wish_room":
            classroom = get_classes().get_classroom(
                self.course_data["CLASS"], null_ok=True
            )
            result = RoomDialog.popup(
                start_value=lthis["ROOM"],
                classroom=classroom,
                parent=self
            )
            if result is not None:
                db_update_field(
                    "LESSON_DATA",
                    "ROOM",
                    result,
                    Lesson_data=lthis["Lesson_data"]
                )
                self.load_course_table(lesson_id=lid)
        ### BLOCK (LESSON_GROUPS)
        elif object_name == "block_name":
            row = self.lesson_table.currentRow()
            assert row >= 0
            result = BlockNameDialog.popup(
                # <course_data> is necessary for courses with no "lessons"
                # Otherwise the data could be taken from <course_lessons>.
                course_lessons=self.course_lessons,
                lesson_row=row,
                parent=self
            )
            if result is not None:
                bsid, btag = result
                db_update_fields(
                    "LESSON_GROUPS",
                    [("BLOCK_SID", bsid), ("BLOCK_TAG", btag)],
                    lesson_group=lthis["Lesson_group"]
                )
                # Redisplay
                self.load_course_table(lesson_id=lid)
        ### NOTES (LESSON_GROUPS)
        elif object_name == "notes":
            result = TextLineDialog.popup(lthis["NOTES"], parent=self)
            if result is not None:
                db_update_field(
                    "LESSON_GROUPS",
                    "NOTES",
                    result,
                    lesson_group=lthis["Lesson_group"]
                )
                self.load_course_table(lesson_id=lid)
        ### LENGTH (LESSONS) --- own handler: on_lesson_length_ ...
        ### TIME (LESSONS)
        elif object_name == "wish_time":
            result = DayPeriodDialog.popup(
                start_value=lthis["TIME"],
                parent=self
            )
            if result is not None:
                db_update_field(
                    "LESSONS",
                    "TIME",
                    result,
                    lid=lid
                )
                self.load_course_table(lesson_id=lid)
        ### PARALLEL (LESSONS)
        else:
            assert object_name == "parallel", (
                f"Click event on object {object_name}"
            )
            result = ParallelsDialog.popup(
                self.current_parallel_tag, parent=self
            )
            if result is not None:
                if self.current_parallel_tag.TAG:
                    # There is already a parallel record
                    if result.TAG:
                        # Change the tag and/or weighting
                        db_update_fields(
                            "PARALLEL_LESSONS",
                            [
                                ("TAG", result.TAG),
                                ("WEIGHTING", result.WEIGHTING),
                            ],
                            lesson_id = lid,
                        )
                    else:
                        # Remove the record
                        db_delete_rows(
                            "PARALLEL_LESSONS",
                            lesson_id = lid,
                        )
                else:
                    assert result.TAG
                    # Make a new parallel record
                    db_new_row(
                        "PARALLEL_LESSONS",
                        lesson_id = lid,
                        TAG=result.TAG,
                        WEIGHTING=result.WEIGHTING,
                    )
                self.current_parallel_tag = result
                self.load_course_table(lesson_id=lid)

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

#TODO--
            print("\n§total_calc: TODO")
            print("\n§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§§\n")
            for c in self.course_table.records:
                print("  ---", c)
#        return
#TODO: for teachers?
#workload = course_data.course.Lesson_block.WORKLOAD
#if workload < 0.0:
#    workload *= - nlessons
#tlist = [
#    f"{t.Teacher.TID}: {print_fix(workload * t.PAY_FACTOR)}"
#    for t in course_data.teacher_list
#]
#return "; ".join(tlist)

            if self.filter_value == 0:
                self.ui.total.clear()
                self.ui.total.setEnabled(False)
            else:
                nlessons, total = workload_teacher(
                    self.filter_value, self.course_table.records
                )
            self.ui.total.setText(T["TEACHER_TOTAL"].format(
                n=nlessons, total=total
            ))
            self.ui.total.setEnabled(True)
        else:
            self.ui.total.clear()
            self.ui.total.setEnabled(False)

#    @Slot(str)
#    def on_lesson_length_textActivated(self, i):
#        ival = int(i)
#        lthis = self.current_lesson[1]
#        if lthis["LENGTH"] != ival:
#            lid = lthis["Lid"]
#            db_update_field(
#                "LESSONS",
#                "LENGTH", ival,
#                lid=lid
#            )
#            # Redisplay
#            self.load_course_table(lesson_id=lid)

#    @Slot()
#    def on_new_element_clicked(self):
#        """Add an item type: block, simple lesson or no-lesson/pay-only.
#        The item can be completely new or share a LESSON_GROUP, and
#        possibly a LESSON_DATA, entry.
#        All the fiddly details are taken care of in <NewCourseLessonDialog>,
#        which should only return valid results.
#        If a completely new simple or block lesson is added, a single
#        lesson is also added to the LESSONS table.
#        """
#        # <self.course_data> is – effectively – a random record for the
#        # current course, the first one in the list returned by
#        # <filter_activities(...)>.
#        # It is not necessarily that of the currently selected "lesson".
##TODO--
#        print("?????", self.course_data)
#
#        bn = NewCourseLessonDialog.popup(self.course_data)
#        if not bn:
#            return
##TODO--
#        print("? ->", bn)
#
#        l= -1
#        lg = bn["Lesson_group"]
#        ld = bn.get("Lesson_data", -1)
#        if lg < 0:
#            bsid = bn["BLOCK_SID"]
#            btag = bn["BLOCK_TAG"]
#            if bsid:
#                # new block
#                lg = db_new_row(
#                    "LESSON_GROUPS",
#                    BLOCK_SID=bsid,
#                    BLOCK_TAG=btag,
#                    NOTES=""
#                )
#                ld = db_new_row(
#                    "LESSON_DATA",
#                    Pay_factor_id=get_default_pay_factor_id(),
#                    PAY_NLESSONS="1",
#                    ROOM=""
#                )
#                cl_id = db_new_row(
#                    "COURSE_LESSONS",
#                    Course=self.course_id,
#                    Lesson_group=lg,
#                    Lesson_data=ld
#                )
#                l = db_new_row(
#                    "LESSONS",
#                    Lesson_group=lg,
#                    LENGTH=1,
#                    TIME="",
#                    PLACEMENT="",
#                    ROOMS=""
#                )
#            elif btag == "$":
#                # new payment-only
#                lg = 0
#                l = 0
#                ld = db_new_row(
#                    "LESSON_DATA",
#                    Pay_factor_id=get_default_pay_factor_id(),
#                    PAY_NLESSONS="1",
#                    ROOM=""
#                )
#                cl_id = db_new_row(
#                    "COURSE_LESSONS",
#                    Course=self.course_id,
#                    Lesson_group=lg,
#                    Lesson_data=ld
#                )
#            else:
#                assert not btag
#                # new simple lesson
#                lg = db_new_row(
#                    "LESSON_GROUPS",
#                    BLOCK_SID="",
#                    BLOCK_TAG="",
#                    NOTES=""
#                )
#                ld = db_new_row(
#                    "LESSON_DATA",
#                    Pay_factor_id=get_default_pay_factor_id(),
#                    PAY_NLESSONS="-1",
#                    ROOM=""
#                )
#                cl_id = db_new_row(
#                    "COURSE_LESSONS",
#                    Course=self.course_id,
#                    Lesson_group=lg,
#                    Lesson_data=ld
#                )
#                l = db_new_row(
#                    "LESSONS",
#                    Lesson_group=lg,
#                    LENGTH=1,
#                    TIME="",
#                    PLACEMENT="",
#                    ROOMS=""
#                )
#        else:
#            if ld < 0:
#                ld = db_new_row(
#                    "LESSON_DATA",
#                    Pay_factor_id=bn["Pay_factor_id"],
#                    PAY_NLESSONS=bn["PAY_NLESSONS"],
#                    ROOM=""
#                )
#            cl_id = db_new_row(
#                "COURSE_LESSONS",
#                Course=self.course_id,
#                Lesson_group=lg,
#                Lesson_data=ld
#            )
#            if lg == 0:
#                l = 0
#        # Redisplay
#        self.load_course_table(lesson_id=l)

    @Slot()
    def on_lesson_add_clicked(self):
        """Add a lesson to the current element. If this is a block, that
        of course applies to the other participating courses as well.
        If no element (or a pay-only element) is selected, this button
        should be disabled.
        """
        lthis = self.current_lesson[1]
        newid = db_new_row(
            "LESSONS",
            lesson_group=lthis["Lesson_group"],
            LENGTH=lthis["LENGTH"]
        )
        self.load_course_table(lesson_id=newid)

    @Slot()
    def on_lesson_sub_clicked(self):
        """Remove a lesson from the current element. If this is a block,
        the removal of course applies to the other participating courses
        as well. If no element, a pay-only element or an element with
        only one lesson is selected, this button should be disabled.
        """
        lthis = self.current_lesson[1]
        newids = db_values(
            "LESSONS",
            "Lid",
            lesson_group=lthis["Lesson_group"]
        )
        newids.remove(lid := lthis["Lid"])
        assert newids, (
            f"Tried to delete LESSON with Lid={lid}"
            " although it is the only one for this element"
        )
        db_delete_rows("LESSONS", Lid=lid)
        self.load_course_table(lesson_id=newids[-1])

#    @Slot()
#    def on_remove_element_clicked(self):
#        """Remove the current element (pay-only or lesson-group) from
#        the current course – that is the COURSE_LESSONS entry.
#        If there are no other COURSE_LESSONS entries with the same
#        lesson-group, the associated lessons will also be deleted.
#        """
#        cldata = self.current_lesson[1]
#        lg = cldata["Lesson_group"]
#        ld = cldata["Lesson_data"]
#        # Delete COURSE_LESSONS entry
#        db_delete_rows("COURSE_LESSONS", Cl_id=cldata["Cl_id"])
#        # Delete associated lessons if they are no longer referenced
#        if not db_values(
#            "COURSE_LESSONS",
#            "Cl_id",
#            lesson_group=lg
#        ):
#            db_delete_rows("LESSONS", Lesson_group=lg)
#        # Delete LESSON_DATA entry if it is no longer referenced
#        if not db_values(
#            "COURSE_LESSONS",
#            "Cl_id",
#            Lesson_data=ld
#        ):
#            db_delete_rows("LESSON_DATA", Lesson_data=ld)
#        # Reload course data
#        self.load_course_table()

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
