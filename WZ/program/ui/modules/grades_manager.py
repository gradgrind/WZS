"""
ui/modules/grades_manager.py

Last updated:  2024-01-20

Front-end for managing grade reports.


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
T = Tr("ui.modules.grades_manager")

### +++++

from typing import Optional
import datetime
import json

from ui.ui_base import (
    load_ui,
    ### QtWidgets:
    QWidget,
#    QHeaderView,
#    QAbstractButton,
    QTableWidgetItem,
    QStyledItemDelegate,
    QLineEdit,
    QComboBox,
    QDialog,
    QVBoxLayout,
    QCalendarWidget,
    QTextEdit,
    QDialogButtonBox,
    QListWidget,
    QStyle,
    #QCompleter,
    ### QtGui:
    QColor,
#    QBrush,
    QValidator,
    ### QtCore:
    QObject,
    Qt,
    QEvent,
    QTimer,
    QDate,
    Slot,
    QPoint,
    ### other
    APP,
#    SHOW_CONFIRM,
    SAVE_FILE,
)
from ui.rotated_table_header import RotatedHeaderView
from ui.table_support import CopyPasteEventFilter

from core.base import (
    REPORT_INFO,
    REPORT_ERROR,
    REPORT_WARNING,
    REPORT_CRITICAL,
)
from core.basic_data import get_database, CONFIG
from core.db_access import db_TableRow
from core.dates import print_date
from core.list_activities import report_data
#from core.classes import class_group_split_with_id
from grades.grade_tables import (
    #subject_map,
    grade_scale,
    valid_grade_map,
    DelegateColumnInfo,
    GradeTable,
)
from grades.grade_tables import grade_table_data
from grades.ods_template import BuildGradeTable
import local

UPDATE_PAUSE = 1000     # time between cell edit and db update in ms

### -----


class TableItem(QTableWidgetItem):
    """A custom table-widget-item which differentiates (minimally)
    between EditRole and DisplayRole, currently only for displaying
    the value – no distinct values are saved.
    It also uses the table item-delegate to handle validation when
    pasting and displaying values.
    """
    def data(self, role: Qt.ItemDataRole):
        val = super().data(role)
        if role == Qt.ItemDataRole.DisplayRole:

            col = self.column()
            delegate = self.tableWidget().itemDelegate()
            gt = delegate.data
            dci = gt.column_info[col]

            if dci.TYPE == "DATE" and val:
                return print_date(val, trap = False) or "???"
            else:
                if gt.validate(col, val):
                    return "??"
        return val

    def paste_cell(self, value: str):
        """This handles paste operations, validating the value.
        """
        row, col = self.row(), self.column()
        delegate = self.tableWidget().itemDelegate()
        bad_field = delegate.data.validate(col, value, write = True)
        if bad_field:
            REPORT_ERROR(T("PASTE_VALUE_ERROR",
                row = row + 1,
                col = bad_field,
                value = value
            ))
            return False
        # Set value in table
        self.setText(value)
        # Trigger database update
        delegate.cell_edited(row, col, value)
        return True


class EscapeKeyEventFilter(QObject):
    """Implement an event filter to catch escape-key presses.
    """
    def __init__(self, widget, callback):
        super().__init__()
        widget.installEventFilter(self)
        self._widget = widget
        self._callback = callback

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                #print("§escape")
                self._callback()
                #return True
        # otherwise standard event processing
        return False


class TableComboBox(QComboBox):
    """A QComboBox adapted for use as a table delegate.
    The main point is that the "closed" box is never shown.
    """
    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self.activated.connect(self._activated)
        print("§view:", self.view(), hex(self.view().windowFlags()))
        self.escape_filter = EscapeKeyEventFilter(self.view(), self.esc)

    def esc(self):
        #print("§esc")
        self.hidePopup()
        self._callback(self)

    def _activated(self, i):
        # Not called on ESC
        #print("§activated:", i)
        self._callback(self)


class GradeTableDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super().__init__(parent)
        ## The underlying grade table data, set in <init()>
        self.data = None
        #print("?????CONFIG:", CONFIG._map)
        self._M_width = self.parent().fontMetrics().horizontalAdvance("M")
        #print("§M:", self._M_width)
        # Date field delegate
        w = self._max_width([print_date("2024-12-30")])
        self._min_date_width = w + self._M_width
        # Use a "dummy" line editor (because it seems to work, while
        # other approaches are a bit difficult to get working ...)
        self._editor = QLineEdit()
        self._editor.setReadOnly(True)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self.update_db)

    def destroyEditor(self, editor,  index):
        """Reimplement <destroyEditor> to do nothing because the editors
        are retained.
        """
        pass
        #print("§destroyEditor ... or not!")

    def createEditor(self, parent, option, index):
        ctype = self.data.column_info[index.column()].TYPE
        if ctype.endswith("!"):
            # read-only
            return None
        self._primed = None
        if ctype == "GRADE":
            self._grade_editor.setParent(parent)
            return self._grade_editor
        else:
            self._editor.setParent(parent)
            return self._editor
#TODO: other types?

    def setEditorData(self, editor, index):
        row, col = index.row(), index.column()
        dci = self.data.column_info[col]
        ctype = dci.TYPE
        if ctype == "CHOICE":
            # For some reason (!?), this gets called again after the new
            # value has been set, thus the use of <self._primed>.
            if self._primed is None:
                self._primed = self.data.read(row, col)
                print("§ACTIVATE", self._primed)
                QTimer.singleShot(0, lambda: self.popup_choice(
                    dci.DATA
                ))
                return
            #else:
            #    print("§REPEATED ACTIVATION")
        elif ctype == "DATE":
            # For some reason (!?), this gets called again after the new
            # value has been set, thus the used of <self._primed>.
            if self._primed is None:
                self._primed = self.data.read(row, col)
                print("§ACTIVATE", self._primed)
                QTimer.singleShot(0, lambda: self.popup_cal(editor))
                return
            #else:
            #    print("§REPEATED ACTIVATION")

#TODO: COMPOSITE, AVERAGE
# Would I want to differentiate between "in-place" text (short) and
# pop-up (long) text entry?
# COMPOSITE and AVERAGE should probably have handlers in "local" code.

# Some fields are read-only, some are not saved to the GRADES table.
# It is (perhaps) possible that there are fields which belong to only
# one of these two categories.
# One possibility would be to incorporate this information in the
# field names (e.g. prefix '-' for no-save, suffix '#' for read-only).

# I probably need a link to the table widget to have access to the
# key-value information for the cells. Or I use the "changed" signal?
        elif ctype == "TEXT":
            # For some reason (!?), this gets called again after the new
            # value has been set, thus the used of <self._primed>.
            if self._primed is None:
                self._primed = self.data.read(row, col)
                print("§ACTIVATE", self._primed)
                QTimer.singleShot(0, self.popup_text)
                return
            #else:
            #    print("§REPEATED ACTIVATION")

        super().setEditorData(editor, index)

    def popup_cal(self, editor):
        """Calendar popup.
        """
        cal = Calendar(editor)
        self._editor.setText(self._primed)
        text = cal.open(self._primed)
        if text is not None:
            self._editor.setText(text)
        #print(f"Calendar {self._primed} -> {text}")
        print("§editor-parent:", self._editor.parent())
        # Ensure the edited cell regains focus
        self._editor.parent().setFocus(Qt.FocusReason.PopupFocusReason)
        # Finish editing
        self.commitData.emit(self._editor)
        self.closeEditor.emit(self._editor)

    def popup_text(self):
        """Text popup, for longer texts.
        """
        te = TextEditor(self._editor)
        self._editor.setText(self._primed)
        text = te.open(self._primed)
        if text is not None:
            self._editor.setText(text)
        # Ensure the edited cell regains focus
        self._editor.parent().setFocus(Qt.FocusReason.PopupFocusReason)
        # Finish editing
        self.commitData.emit(self._editor)
        self.closeEditor.emit(self._editor)

    def popup_choice(self, items: list[str]):
        """List popup, choose one entry (or escape).
        """
        lc = ListChoice(self._editor)
        self._editor.setText(self._primed)
        text = lc.open(items, self._primed)
        #text = lc.open(self._primed)
        #text = lc.text()
        if text is not None:
            self._editor.setText(text)
        # Ensure the edited cell regains focus
        self._editor.parent().setFocus(Qt.FocusReason.PopupFocusReason)
        # Finish editing
        self.commitData.emit(self._editor)
        self.closeEditor.emit(self._editor)

#TODO: This can probably be simplified by handling writing myself.
# I could even dispense with the special table widget by writing only
# display values to the table.
    def setModelData(self, editor, model, index):
        """Reimplement to handle cells set by functions.
        Trigger line processing via a delay, so that multiple updates to
        a single line can all be processed together.
        """
        # First perform standard update
        super().setModelData(editor, model, index)

        '''
        # Use "properties" to get the value
        metaobject = editor.metaObject()
        #print("%%1:", dir(metaobject))
        for i in range(metaobject.propertyCount()):
            metaproperty = metaobject.property(i)
            if metaproperty.isUser():
                name = metaproperty.name()
                #print("%%name:", name)
                #print("%%value:", editor.property(name))
                #print("%%user:", metaproperty.isUser())
                text = editor.property(name)
        model.setData(index, text, Qt.ItemDataRole.EditRole)
        '''

        r, c = index.row(), index.column()
        d = model.data(index, Qt.ItemDataRole.EditRole)
        self.cell_edited(r, c, d)

    def cell_edited(self, row, col, value):
        #print("§CHANGED:", row, col, value)
        try:
            self._pending_changes[row][col] = value
        except KeyError:
            self._pending_changes[row] = {col: value}
        # If the timer is already running, this will stop and restart it
        self._timer.start(UPDATE_PAUSE)

    @Slot()
    def update_db(self):
        """Automatic update of calculated fields and writing of changed
        data to database.
        Update one row and start the timer again with minimal delay to
        allow pending events to be processed before the next row.
        """
        for r, cd in self._pending_changes.items():
            if cd:
                break
        else:
            return
#TODO
        print("§update_db:", r, cd)
        tw = self.parent()
        for c in self.data.calculate_row(r):
            # Write to display table
            val = self.data.read(r, c)
            tw.item(r, c).setText(val)
        self._pending_changes[r] = {}
        self._timer.start(0)

#########################++

#TODO: deprecated (see version in <GradeTable>
    def calculate_row(self, row: int) -> list[tuple[int, str]]:
        REPORT_WARNING("TODO: GradeTableDelegate.calculate_row is deprecated")
        tw = self.parent()
        col_values = []
        calculated_values = []
        for c, coldata in enumerate(self._columns):
            ctype = coldata.TYPE
            if ctype[-1] == "!":
                # Calculate the value
                val = self.grade_arithmetic.function(
                    coldata.DATA, col_values
                )
                calculated_values.append((len(col_values), val))
            else:
                val = tw.item(row, c).data(Qt.ItemDataRole.EditRole)
            col_values.append(val)
            #print("§VALUE:", ctype, coldata.NAME, val)
        return calculated_values

#TODO: deprecated (see version in <GradeTable>
    def validate(self, col: int, value: str, write: bool = False
    ) -> Optional[str]:
        """Checks that the value is valid for the given column.
        Return the LOCAL name if invalid, <None> if valid.
        """
        REPORT_WARNING("TODO: GradeTableDelegate.validate is deprecated")
        coldata = self._columns[col]
        ctype = coldata.TYPE
        ok = True
        if ctype.startswith("GRADE"):
            if value not in self._grade_validator._values:
                ok = False
        elif ctype == "CHOICE":
            if value not in coldata.DATA:
                ok = False
        elif ctype == "DATE":
            try:
                datetime.datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                ok = False
        elif ctype[-1] == "!":
            ok = not write
        # Other column types are not checked
        if ok:
            return None
        return coldata.LOCAL

#########################--

    def _max_width(self, string_list: list[str]) -> tuple[int, int]:
        """Return the display width of the widest item in the list.
        """
        fm = self.parent().fontMetrics()
        w = 0
        for s in string_list:
            _w = fm.boundingRect(s).width()
            if _w > w:
                w = _w
        return w

    def _done(self, editor):
        print("§done", self._primed)
        if self._primed is not None:
            # Ensure the edited cell regains focus
            editor.parent().setFocus(Qt.FocusReason.PopupFocusReason)
            # Finish editing
#            self.commitData.emit(editor)
#            self.closeEditor.emit(editor)

    def init(self, data: GradeTable) -> list[int]:
        """Call this when initializing a table for a new group.
        Return a list of column widths.
        """
        self.data = data
        glist = list(data.grade_map)
        self._min_grade_width = self._max_width(glist) + self._M_width
        self._pending_changes = {}
        self._grade_editor = QLineEdit()
        self._grade_validator = ListValidator(glist)
        self._grade_editor.setValidator(self._grade_validator)
        return [self._column_width(dci) for dci in data.column_info]

    def _column_width(self, grade_field) -> int:
        """Return the minimum width for the column.
        """
        if grade_field is None:
            REPORT_CRITICAL(
                "Bug: Grade table column with no type specification"
            )
        ctype = grade_field.TYPE
        #print("§grade_field:", grade_field)
        # Default values:
        w = 50
        if ctype == "GRADE":
            w = self._min_grade_width
        elif ctype == "COMPOSITE!":
            w = self._min_grade_width + self._M_width
        elif ctype == "CHOICE":
            w = self._max_width(grade_field.DATA) + self._M_width * 2
        elif ctype == "DATE":
            w = self._min_date_width
        elif ctype == "TEXT":
            w = self._max_width(["Text field width"])
        elif ctype == "FUNCTION!":
            pass
        elif ctype != "DEFAULT":
            REPORT_ERROR(f"TODO:: Unknown column type: '{ctype}'")
            grade_field.TYPE = "DEFAULT"
        return w


class ListValidator(QValidator):
    def __init__(self, values: list[str], parent = None):
        super().__init__(parent)
        self._values = set(values)

    def validate(self, text: str, pos: int):
        #QValidator.State.Acceptable
        #QValidator.State.Invalid
        #QValidator.State.Intermediate
        if text in self._values:
            return (QValidator.State.Acceptable, text, pos)
        else:
            return (QValidator.State.Intermediate, text, pos)


class ListChoice(QDialog):
    def __init__(self, parent = None):
        super().__init__(parent = parent)
        self.setWindowFlags(Qt.WindowType.SplashScreen)
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        self.listwidget = QListWidget()
        self.listwidget.setStyleSheet("QListView::item {padding: 3px}")
        vbox.addWidget(self.listwidget)
        self.listwidget.itemClicked.connect(self.done_ok)
        self.listwidget.itemActivated.connect(self.done_ok)

    def open(self, items: list[str], value: str = None):
        self.result = None
        self.listwidget.clear()
        row = 0
        for i, s in enumerate(items):
            if s == value:
                row = i
            self.listwidget.addItem(s)
        lw = self.listwidget
        w = lw.sizeHintForColumn(0) + lw.frameWidth() * 2
        h = lw.sizeHintForRow(0) * lw.count() + 2 * lw.frameWidth()
        if h > 200:
            h = 200
            scrollBarWidth = lw.style().pixelMetric(
                QStyle.PixelMetric.PM_ScrollBarExtent
            )
            w += scrollBarWidth + lw.width() - lw.viewport().width()
        lw.setFixedSize(w, h)
        self.resize(0, 0)
        self.listwidget.setCurrentRow(row)
        p = self.parent()
        if p:
            self.move(p.mapToGlobal(QPoint(0, 0)))
        self.exec()
        return self.result

    def done_ok(self, item):
        self.result = item.text()
        self.accept()


class Calendar(QDialog):
    def __init__(self, parent = None):
        super().__init__(parent = parent)
        self.cal = QCalendarWidget()
        vbox = QVBoxLayout(self)
        vbox.addWidget(self.cal)
        self.cal.clicked.connect(self._choose1)
        self.cal.activated.connect(self._choose)

    def _choose1(self, date: QDate):
        #print("§CLICKED:", date)
        self.cal.setSelectedDate(date)
        self.result = date.toString(Qt.DateFormat.ISODate)
        QTimer.singleShot(200, self.accept)

    def _choose(self, date: QDate):
        self.result = date.toString(Qt.DateFormat.ISODate)
        self.accept()

    def open(self, text = None):
        self.result = None
        #print("§open:", text)
        if text:
            self.cal.setSelectedDate(
                QDate.fromString(text, Qt.DateFormat.ISODate)
            )
        self.exec()
        return self.result


class TextEditor(QDialog):
    def __init__(self, parent = None):
        super().__init__(parent = parent)
        self.te = QTextEdit()
        vbox = QVBoxLayout(self)
        vbox.addWidget(self.te)
        self.bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Reset
        )
        vbox.addWidget(self.bb)
        self.bb.accepted.connect(self.done_ok)
        self.bb.rejected.connect(self.close)
        self.bb.button(
            QDialogButtonBox.StandardButton.Reset
        ).clicked.connect(self.reset)
        self.te.textChanged.connect(self.changed)

    def reset(self):
        self.result = ""
        self.accept()

    def done_ok(self):
        self.result = '¶'.join(self.current.splitlines())
        self.accept()

    def open(self, text = None):
        self.result = None
        self.suppress_handlers = True
        #print("§open:", text)
        self.text0 = text.replace('¶', '\n') if text else ""
        self.te.setPlainText(self.text0)
        self.suppress_handlers = False
        self.changed()
        p = self.parent()
        if p:
            self.move(p.mapToGlobal(QPoint(0, 0)))
        self.exec()
        return self.result

    def changed(self):
        if self.suppress_handlers: return
        self.current = self.te.toPlainText()
        self.bb.button(QDialogButtonBox.StandardButton.Ok).setDisabled(
            self.current == self.text0
        )


class ManageGradesPage(QObject):
    def colour_cache(self, colour: str) -> QColor:
        try:
            qc = self._colours[colour]
        except KeyError:
            qc = QColor(colour)
            self._colours[colour] = qc
        return qc

    def __init__(self, parent = None):
        self._colours = {}
        super().__init__()
        self.ui = load_ui("grades.ui", parent, self)
        tw = self.ui.grade_table
        delegate = GradeTableDelegate(parent = tw)
        tw.setItemDelegate(delegate)
        self.event_filter = CopyPasteEventFilter(tw)
        headerView = RotatedHeaderView()
        tw.setHorizontalHeader(headerView)
        headerView.setStretchLastSection(True)
        headerView.setMinimumSectionSize(20)
        tw.clear()
        m = headerView._margin
        tw.setStyleSheet(
#            "QTableView {"
#                "selection-background-color: #f0e0ff;"
#                "selection-color: black;"
#            "}"
#            "QTableView::item:focus {"
#                "background-color: #e0a0ff;"
#            "}"
            f"QHeaderView::section {{padding: {m}px;}}"
        )

    def enter(self):
        # Set up lists of classes, teachers and subjects for the course
        # filter. These are lists of tuples:
        #    (db-primary-key, short form, full name)
        self.db = get_database()
        self.report_info = report_data(GRADES = True)[0] # only for the classes
        ## Set up widgets
        self.suppress_handlers = True
        # Set up the "occasions" choice.
        self.ui.combo_occasion.clear()
        self.occasions = [
            (k, v.split())
            for k, v in json.loads(CONFIG.GRADE_OCCASION).items()
        ]
        self.occasions.sort()
        self.ui.combo_occasion.addItems(p[0] for p in self.occasions)
        self.ui.combo_occasion.setCurrentIndex(-1)
        self.fill_group_list()

        # Activate the window
        self.suppress_handlers = False

    ### actions ###

    def fill_group_list(self):
        self.ui.combo_group.clear()
        i = self.ui.combo_occasion.currentIndex()
        if i < 0: return
        olist = self.occasions[i][1]
        self.ui.combo_group.addItems(olist)
        if len(olist) > 1:
            self.ui.combo_group.setCurrentIndex(-1)
        elif olist:
            self.ui.combo_group.setCurrentIndex(0)

    def set_group(self):
        self.suppress_handlers = True
        o = self.ui.combo_occasion.currentIndex()
        i = self.ui.combo_group.currentIndex()
        o_item = self.occasions[o]
        self.class_group = o_item[1][i]
        self.occasion = o_item[0]
        print("§on_combo_group_currentIndexChanged:",
            repr(self.occasion), self.class_group
        )
#        self.occasion_tag = self.ui.occasion_extra.currentText()
#TODO: Remove or replace this when the occasion-tag handling is implemented:
#        assert self.occasion_tag == ""
#        if '$' in self.occasion:
#            REPORT_ERROR("TODO: '$'-occasions not yet implemented")
#            self.ui.grade_table.clear()
#            return
# Consider removing this category: couldn't I simply add all tables to
# the occasions list?


        tw = self.ui.grade_table
        tw.clear()

###########################******

        grade_table = GradeTable(
            self.occasion, self.class_group, self.report_info
        )

        ## Set the table size
        headers = [dci.LOCAL for dci in grade_table.column_info]
        tw.setColumnCount(len(headers))
        vheaders = [gtline.student_name for gtline in grade_table.lines]
        tw.setRowCount(len(vheaders))
        tw.setHorizontalHeaderLabels(headers)
        tw.setVerticalHeaderLabels(vheaders)

        delegate = tw.itemDelegate()
        for i, w in enumerate(delegate.init(grade_table)):
            tw.setColumnWidth(i, w)


#        return


        ### Fill the table
        for i, gtline in enumerate(grade_table.lines):
            pname = gtline.student_name
            values = gtline.values
            # Add grades, etc.
            for j, dci in enumerate(grade_table.column_info):
                item = TableItem(values[j])
                item.setBackground(self.colour_cache(dci.COLOUR))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tw.setItem(i, j, item)

#TODO: What about calculated fields that need storing in the grade map
# (flag G)?
###########################--

        self.suppress_handlers = False

#TODO: This is a fix for a visibility problem (gui refresh)
        for w in APP.topLevelWindows():
            if w.isVisible():
                w.show()

        return

#-----------------------------------------------------

        _info, subject_list, student_list = grade_table_data(
            occasion = self.occasion,
            class_group = self.class_group,
            report_info = self.report_info,
            grades = self.db.table("GRADES").grades_occasion_group(
                self.occasion, self.class_group
            ),
        )
        ## Set up grade arithmetic and validation
        gscale = grade_scale(self.class_group)
        grade_map = valid_grade_map(gscale)
        ### Collect the columns
        headers = []
        col_colours = []
        col_dci = []       # collect <DelegateColumnInfo> objects
        key_col = {}
        all_grade_cols = set() # collect columns with grades for "*"

        gfields = self.db.table("GRADE_FIELDS").records
        for gf_i, rec in enumerate(gfields):
            gl = rec.GROUPS
            if gl != '*' and self.class_group not in gl.split():
                continue
            # Convert "sid" lists to column lists. Note that only columns
            # that have already been added can be included!
            try:
                sids = rec.DATA["__SIDS__"]
            except (TypeError, KeyError):
                pass
            else:
                cols = []
                if sids == "*":
                    # All non-component grades, including composites
                    for i, dci in enumerate(col_dci):
                        if dci.TYPE == "GRADE":
                            if "C" not in dci.FLAGS:
                                cols.append(i)
                        elif dci.TYPE == "COMPOSITE!":
                            cols.append(i)
                else:
                    for sid in sids.split():
                        try:
                            cols.append(key_col[sid])
                        except KeyError:
                            pass
                rec.DATA["__COLUMNS__"] = cols
                #print("§__COLUMNS__:", rec.NAME, cols)
            ctype = rec.TYPE
            if ctype == "GRADE":
                ## Add the grade columns
                for sbj in subject_list:
                    i = len(headers)
                    key_col[sbj.SID] = i
                    headers.append(sbj.NAME)
                    col_colours.append(rec.COLOUR)
                    # collect <DelegateColumnInfo> objects
                    col_dci.append(DelegateColumnInfo(rec,
                        NAME = str(sbj.id),
                        LOCAL = sbj.NAME,
                        DATA = {"SID": sbj.SID}
                    ))
                    all_grade_cols.add(i)
                continue

            if ctype == "COMPOSITE!":
                q_colour = QColor(rec.COLOUR).darker(120)
                components = []
                for col in rec.DATA["__COLUMNS__"]:
                    dci = col_dci[col]
                    if dci.TYPE != "GRADE":
                        REPORT_ERROR(T("COMPONENT_NOT_GRADE",
                            subject = rec.NAME,
                            sid = dci.NAME
                        ))
                        continue
                    if "C" in dci.FLAGS:
                        REPORT_ERROR(T("COMPONENT_NOT_UNIQUE",
                            sid = dci.DATA["SID"]
                        ))
                        continue
                    # Mark as component
                    dci.FLAGS += "C"
                    all_grade_cols.discard(col)
                    components.append(col)
                    col_colours[col] = q_colour
                if not components:
                    REPORT_WARNING(T("COMPOSITE_WITHOUT_COMPONENTS",
                        subject = rec.NAME
                    ))
                    continue
                if rec.LOCAL:
                    all_grade_cols.add(len(headers))
                    rec.DATA["__COLUMNS__"] = components
                    dci = DelegateColumnInfo(rec)
                else:
                    continue

            elif rec.LOCAL:
                dci = DelegateColumnInfo(rec)

            else:
                continue

            key_col[rec.NAME] = len(headers)
            headers.append(rec.LOCAL)
            col_dci.append(dci)
            col_colours.append(rec.COLOUR)
###########################--
        ## Set the table size
        tw.setColumnCount(len(headers))
        nrows = len(student_list)
        tw.setRowCount(nrows)
        tw.setHorizontalHeaderLabels(headers)

#        print("))) Table size set:", nrows, len(headers))

#TODO: Can/should LEVEL be optional? I would also need to look at the
# grade_tables (?) module
# There may be other fields in the students (extra) data – get these fields
# from GRADE_FIELDS (flag S).
# There may also be fields whose default values are in the calendar, or
# elsewhere. These would also need to be handled appropriately.

        delegate = tw.itemDelegate()
        delegate.init(subject_list, grade_map)
        for i, dci in enumerate(col_dci):
            tw.setColumnWidth(i, delegate.add_column(dci))

###########################++

        ### Fill the table
        vheaders = []
        for i, stdata in enumerate(student_list):
            #print("%stadata:", stdata)
            pname = stdata["NAME"]
            vheaders.append(pname)
            grades = stdata["GRADES"]
            # Add grades, etc.
            for j, dci in enumerate(col_dci):
                val = grades.get(dci.NAME) or ""
                colour = col_colours[j]
                item = TableItem(val)
                item.setBackground(QColor(colour))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tw.setItem(i, j, item)

            for c, v in delegate.calculate_row(i):
                #print("§calculate_row:", i, c, v)
                tw.item(i, c).setText(v)
#TODO: What about calculated fields that need storing in the grade map
# (flag G)?
###########################--

        tw.setVerticalHeaderLabels(vheaders)
        self.suppress_handlers = False

#TODO: This is a fix for a visibility problem (gui refresh)
        for w in APP.topLevelWindows():
            if w.isVisible():
                w.show()


###################################


    ### slots ###

    @Slot(int)
    def on_combo_occasion_currentIndexChanged(self, i):
        if self.suppress_handlers: return
        self.suppress_handlers = True
        self.fill_group_list()
        self.suppress_handlers = False
        if self.ui.combo_group.currentIndex() >= 0:
            self.set_group()

    @Slot(int)
    def on_combo_group_currentIndexChanged(self, i):
        if self.suppress_handlers: return
        self.set_group()

    @Slot()
    def on_pb_grade_input_table_clicked(self):
        print("§MAKE GRADE TABLE")
        gt = BuildGradeTable(self.occasion, self.class_group)
        fpath = SAVE_FILE(
            f'{T("ods_file")} (*.ods)',
            start = gt.output_file_name
        )#, title=)
        if not fpath:
            return
        if not fpath.endswith(".ods"):
            fpath += ".ods"
        gt.save(fpath)
        REPORT_INFO(T("SAVED_GRADE_TABLE", path = fpath))


#    @Slot(int,int)
#    def on_grade_table_cellActivated(self, row, col):
#        print("§on_grade_table_cellActivated:", row, col)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from ui.ui_base import run
    _db = get_database()

    widget = ManageGradesPage()
    widget.enter()
    widget.ui.resize(1000, 550)
    run(widget.ui)
