"""
ui/modules/grades_manager.py

Last updated:  2024-01-26

Front-end for managing grade reports.

This is an experimental version. It uses Model/View for the group data table
and has initial code to move the grade table to Model/View. The latter is
nearly complete, but may need tweaks. At present the table-widget version
is still used.

It is clear that the Model/View approach offers benefits, but I am not
convinced that I should switch because – actually – I want to keep the
gui as separate as possible from the back-end and the Model/View approach
involves quite extensive interactions.


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

import json

from ui.ui_base import (
    load_ui,
    ### QtWidgets:
    QWidget,
    QTableWidgetItem,
    QStyledItemDelegate,
    QLineEdit,
    QAbstractItemView,
    QCompleter,
    ### QtGui:
    QColor,
    QBrush,
    QValidator,
    ### QtCore:
    QObject,
    Qt,
    QEvent,
    QTimer,
    Slot,
    QPoint,
    QAbstractListModel,
    QModelIndex,
    ### other
    APP,
#    SHOW_CONFIRM,
    SAVE_FILE,
)
from ui.rotated_table_header import RotatedHeaderView
from ui.table_support import (
    CopyPasteEventFilter,
    Calendar,
    TextEditor,
    ListChoice,
)

from core.base import (
    REPORT_INFO,
    REPORT_ERROR,
    REPORT_CRITICAL,
)
from core.basic_data import get_database, CONFIG
from core.dates import print_date
from core.list_activities import report_data
#from core.classes import class_group_split_with_id
from grades.grade_tables import GradeTable
from grades.ods_template import BuildGradeTable

UPDATE_PAUSE = 1000     # time between cell edit and db update in ms

### -----


class GroupDataDelegate(QStyledItemDelegate):
    """A delegate for the group-data table.
    Pop-up editors are handled in the method <createEditor>, which then
    returns no cell editor, everything being done within this method.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self._calendar = Calendar()

    def createEditor(self, parent, option, index):
        r = index.row()
        tw = self.parent()
        model = tw.model()
        value = model.data(index, Qt.ItemDataRole.EditRole)
        dtype = model.data_type(r)
        if dtype == "DATE":
            y = tw.rowViewportPosition(r)
            self._calendar.move(parent.mapToGlobal(QPoint(0, y)))
            v = self._calendar.open(value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                model.setData(index, v, Qt.ItemDataRole.EditRole)
            return None
#TODO: other types?
        return super().createEditor(parent, option, index)


# New attempt!
class _GradeTableDelegate(QStyledItemDelegate):
    """A delegate for the grade table.
    Pop-up editors are handled in the method <createEditor>, which then
    returns no cell editor, everything being done within this method.
    """
    def __init__(self, parent):
        super().__init__(parent)
        ## Pop-up editors
        self._calendar = Calendar()
        self._text_editor = TextEditor()
        self._list_choice = ListChoice()
        self._m_width = parent().fontMetrics().horizontalAdvance("m")
        #print("§m:", self._m_width)

    def setup(self, grade_table):
        """Initialize for a new grade table.
        """
        glist = list(grade_table.grade_map)
        self._min_grade_width = self._max_width(glist) + self._m_width
        self._grade_validator = ListValidator(glist)
        self._grade_completer = (gc := QCompleter(glist))
        gc.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        gc.setCompletionMode(Qt.CompletionMode.UnfilteredPopupCompletion)
        tw = self.parent()
        for i, dci in enumerate(grade_table.column_info):
            w = self._column_width(dci)
            if w >= 0:
                tw.setColumnWidth(i, w)
                tw.showColumn(i)
            else:
                tw.hideColumn(i)

    def _column_width(self, dci) -> int:
        """Return the minimum width for the column.
        """
        try:
            ctype = dci.TYPE
        except:
            REPORT_CRITICAL(
                "Bug: Grade table column with no type specification"
            )
        if "-" in dci.FLAGS:
            return -1   # hide column
        if ctype == "GRADE":
            return self._min_grade_width
        if ctype == "COMPOSITE!":
            return self._min_grade_width + self._m_width
        if ctype == "CHOICE":
            return self._max_width(dci.DATA) + self._m_width * 2
        if ctype == "DATE":
            return self._min_date_width
        if ctype == "TEXT":
            return self._max_width(["Text field width"])
        if ctype != "FUNCTION!" and ctype != "DEFAULT":
            REPORT_ERROR(f"TODO:: Unknown column type: '{ctype}'")
            dci.TYPE = "DEFAULT"
        return self._m_width * 5    # default width

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

    def createEditor(self, parent, option, index):
        row, col = index.row(), index.column()
        tw = self.parent()
        model = tw.model()
        dci = model.get_dci(col)
        value = model.data(index, Qt.ItemDataRole.EditRole)
        ctype = dci.TYPE
        if ctype == "CHOICE":
            y = tw.rowViewportPosition(row)
            x = tw.columnViewportPosition(col)
            self._list_choice.move(parent.mapToGlobal(QPoint(x, y)))
            v = self._list_choice.open(dci.DATA, value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                model.setData(index, v, Qt.ItemDataRole.EditRole)
            return None
        if ctype == "TEXT":
            y = tw.rowViewportPosition(row)
            x = tw.columnViewportPosition(col)
            self._text_editor.move(parent.mapToGlobal(QPoint(x, y)))
            v = self._text_editor.open(value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                model.setData(index, v, Qt.ItemDataRole.EditRole)
            return None
        if ctype == "DATE":
            y = tw.rowViewportPosition(row)
            x = tw.columnViewportPosition(col)
            self._calendar.move(parent.mapToGlobal(QPoint(x, y)))
            v = self._calendar.open(value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                model.setData(index, v, Qt.ItemDataRole.EditRole)
            return None
#TODO: other types?
        e = super().createEditor(parent, option, index)
        if ctype == "GRADE":
            e.setValidator(self._grade_validator)
            e.setCompleter(self._grade_completer)
        return e


class GroupDataModel(QAbstractListModel):
    def set_data(self, dci_list):
        print("§set group data:", dci_list)
        self.beginResetModel()
        self.data_list = dci_list
        self.endResetModel()

#?
    def data_type(self, row: int) -> str:
        return self.data_list[row].TYPE

    def rowCount(self, parent: QModelIndex):
        return len(self.data_list)

    def data(self,
        index: QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ):
        row = index.row()
#TODO:
        if role == Qt.ItemDataRole.DisplayRole:
            return '*' + self.data_list[row].DATA["default"]

        elif role == Qt.ItemDataRole.EditRole:
            return self.data_list[row].DATA["default"]

        #elif role == Qt.FontRole:
        #    if row == 0 and col == 0:  # change font only for cell(0,0)
        #        bold_font = QFont()
        #        bold_font.setBold(True)
        #        return bold_font

        #elif role == Qt.BackgroundRole:
        #    if row == 1 and col == 2:  # change background only for cell(1,2)
        #        return QBrush(Qt.red)

        elif role == Qt.TextAlignmentRole:
            return Qt.Alignment.AlignCenter
        #    # change text alignment only for cell(1,1)
        #    if row == 1 and col == 1:
        #        return Qt.AlignRight | Qt.AlignVCenter

        #elif role == Qt.CheckStateRole:
        #    if row == 1 and col == 0:  # add a checkbox to cell(1,0)
        #        return Qt.Checked

        return None

    def setData(self, index, value, role):
        if role != Qt.ItemDataRole.EditRole:
            return False
        # save value from editor
        self.data_list[index.row()].DATA["default"] = value
#TODO: save to database, adjust grade table?
        # for presentation purposes only:
        #result = repr(value)
        #self.editCompleted.emit(result)
        return True

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEditable | super().flags(index)

    def headerData(self, section: int, orientation, role):
        if (
            role == Qt.DisplayRole
            and orientation == Qt.Orientation.Vertical
        ):
            return self.data_list[section].LOCAL
        return None




###
class GradeTableModel(QAbstractListModel):
    def __init__(self, parent):
        super().__init__(parent = parent)
        # This timer is to delay writing to database of changed grade-map
        # entries. The aim of this delay is so that when multiple changes
        # are made to one entry these will be collected before doing the
        # actual writing.
        self._pending_changes = {}
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self.update_db)

    def brush_cache(self, colour: str) -> QBrush:
        try:
            qb = self._brushes[colour]
        except KeyError:
            qb = QBrush(QColor(colour))
            self._brushes[colour] = qb
        return qb

    def set_data(self, grade_table):
        for r, cd in self._pending_changes.items():
            if cd:
                REPORT_ERROR("TODO: pending changes not saved")
                break
        self._pending_changes = {}
        self.beginResetModel()
        self.grade_table = grade_table
        self.parent().delegate().setup(grade_table)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex):
        return len(self.grade_table.lines)

    def columnCount(self, parent: QModelIndex):
        return len(self.grade_table.column_info)

    def data(self,
        index: QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ):
        row = index.row()
        col = index.column()
        dci = self.get_dci(col)
        if role == Qt.ItemDataRole.EditRole:
            return self.grade_table.lines[row].values[col]

        elif role == Qt.ItemDataRole.DisplayRole:
            val = self.grade_table.lines[row].values[col]
            if dci.TYPE == "DATE" and val:
                return print_date(val, trap = False) or "???"
            else:
#TODO: use dci instead of col here?
                if self.grade_table.validate(col, val):
                    return "??"
            return val

        elif role == Qt.BackgroundRole:
            return self.brush_cache(dci.COLOUR)

        elif role == Qt.TextAlignmentRole:
            return Qt.Alignment.AlignCenter
        #    return Qt.AlignRight | Qt.AlignVCenter

        #elif role == Qt.FontRole:
        #    if row == 0 and col == 0:  # change font only for cell(0,0)
        #        bold_font = QFont()
        #        bold_font.setBold(True)
        #        return bold_font

        #elif role == Qt.CheckStateRole:
        #    if row == 1 and col == 0:  # add a checkbox to cell(1,0)
        #        return Qt.Checked

        return None

    def setData(self, index, value, role):
        if role != Qt.ItemDataRole.EditRole:
            return False
        row, col = index.row(), index.col()
        self.grade_table.lines[row].values[col] = value
        # Queue change to database
        try:
            self._pending_changes[row][col] = value
        except KeyError:
            self._pending_changes[row] = {col: value}
        # If the timer is already running, this will stop and restart it
        self._timer.start(UPDATE_PAUSE)
        return True

    def get_dci(self, col):
        return self.grade_table.column_info[col]

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
#        tw = self.parent()
#TODO: write to db, how to update display? Does super().setData() need to be
# called? or some signal emitted?
        for c in self.grade_table.calculate_row(r):
            # Write to display table
            val = self.grade_table.read(r, c)
            self.grade_table.lines[r].values[c] = val
        self._pending_changes[r] = {}
        self._timer.start(0)

    def flags(self, index):
        f = super().flags(index)
        if self.get_dci(index.col()).TYPE.endswith("!"):
            return f        # read-only
        return f | Qt.ItemFlag.ItemIsEditable

    def headerData(self, section: int, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.get_dci(section).LOCAL
            if orientation == Qt.Orientation.Vertical:
                return self.grade_table.lines[section].student_name
        return None




#TODO: If I use a QTableView for the grade table, this will be superfluous.
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


class GradeTableDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super().__init__(parent)
        ## The underlying grade table data, set in <set_data()>
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
                #print("§ACTIVATE", self._primed)
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
                #print("§ACTIVATE", self._primed)
                QTimer.singleShot(0, lambda: self.popup_cal(editor))
                return
            #else:
            #    print("§REPEATED ACTIVATION")
        elif ctype == "TEXT":
            # For some reason (!?), this gets called again after the new
            # value has been set, thus the used of <self._primed>.
            if self._primed is None:
                self._primed = self.data.read(row, col)
                #print("§ACTIVATE", self._primed)
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
        #print("§editor-parent:", self._editor.parent())
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
        # Set data in underlying table:
        self.data.lines[row].values[col] = value
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
        tw = self.parent()
        for c in self.data.calculate_row(r):
            # Write to display table
            val = self.data.read(r, c)
            tw.item(r, c).setText(val)
        self._pending_changes[r] = {}
        self._timer.start(0)


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
        if self._primed is not None:
            # Ensure the edited cell regains focus
            editor.parent().setFocus(Qt.FocusReason.PopupFocusReason)
            # Finish editing
#            self.commitData.emit(editor)
#            self.closeEditor.emit(editor)

    def set_data(self, data: GradeTable) -> list[int]:
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
        if "-" in grade_field.FLAGS:
            return -1   # hide column
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
        # group-data table
        dtw = self.ui.date_table
        model = GroupDataModel(dtw)
        dtw.setItemDelegate(GroupDataDelegate(dtw))
        model.set_data([])
        # Apply the model to the list view
        dtw.setModel(model)
        # grade-table
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
        #print("§on_combo_group_currentIndexChanged:",
        #    repr(self.occasion), self.class_group
        #)
        tw = self.ui.grade_table
        dtw = self.ui.date_table
        grade_table = GradeTable(
            self.occasion, self.class_group, self.report_info
        )
        ### Set the table sizes and headers
        headers = []    # grade-table column headers
        dtdata = []     # Underlying data for group-data table
        for dci in grade_table.column_info:
            headers.append(dci.LOCAL)
            if "*" in dci.FLAGS:
                # Add to group-data table
                dtdata.append(dci)
        ## Initialize group-data table
        dtw.model().set_data(dtdata)
        ## Initialize grade table
        tw.clear()
        tw.setColumnCount(len(headers))
        vheaders = [gtline.student_name for gtline in grade_table.lines]
        tw.setRowCount(len(vheaders))
        tw.setHorizontalHeaderLabels(headers)
        tw.setVerticalHeaderLabels(vheaders)
        delegate = tw.itemDelegate()
        for i, w in enumerate(delegate.set_data(grade_table)):
            if w >= 0:
                tw.setColumnWidth(i, w)
                tw.showColumn(i)
            else:
                tw.hideColumn(i)
        ## Fill the grade table
        for i, gtline in enumerate(grade_table.lines):
            values = gtline.values
            # Add grades, etc.
            for j, dci in enumerate(grade_table.column_info):
                item = TableItem(values[j])
                item.setBackground(self.colour_cache(dci.COLOUR))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tw.setItem(i, j, item)
        self.suppress_handlers = False
#TODO: This is a fix for a visibility problem (gui refresh)
        for w in APP.topLevelWindows():
            if w.isVisible():
                w.show()

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
