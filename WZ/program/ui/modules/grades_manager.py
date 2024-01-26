"""
ui/modules/grades_manager.py

Last updated:  2024-01-26

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

import json

from ui.ui_base import (
    load_ui,
    ### QtWidgets:
    QWidget,
    QTableWidgetItem,
    QStyledItemDelegate,
    QLineEdit,
    ### QtGui:
    QColor,
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
from grades.grade_tables import GradeTable, DelegateColumnInfo
from grades.ods_template import BuildGradeTable

UPDATE_PAUSE = 1000     # time between cell edit and db update in ms

### -----


#TODO:
# 1) Move group data table back to QTableWidget.
# 2) Tidying.


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


#TODO: Not needed any more?
'''
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
'''

class GradeTableDelegate(QStyledItemDelegate):
    def __init__(self, table_widget, data_proxy):
        self._table = data_proxy
        super().__init__(parent = table_widget)
        # A basic width unit
        self._m_width = table_widget.fontMetrics().horizontalAdvance("m")
        #print("§m:", self._m_width)
        # Minimum date field width
        w = self._max_width([print_date("2024-12-30")])
        self._min_date_width = w + self._m_width
        ## Pop-up editors
        self._calendar = Calendar()
        self._text_editor = TextEditor()
        self._list_choice = ListChoice()
        self._editor = QLineEdit()

    def createEditor(self, parent, option, index):
        row, col = index.row(), index.column()
        dci = self._table.get_column_info(col)
        value = self._table.read(row, col)
        # The QTableWidget holds the "display" values, so to get the
        # underlying "actual" values, <self._table> is used.
        ctype = dci.TYPE
        # Get the table widget
        tw = self.parent()  # NOT the same as <parent>!
        if ctype == "CHOICE":
            y = tw.rowViewportPosition(row)
            x = tw.columnViewportPosition(col)
            self._list_choice.move(parent.mapToGlobal(QPoint(x, y)))
            v = self._list_choice.open(dci.DATA, value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                self._table.write(row, col, v)
            return None
        if ctype == "TEXT":
            y = tw.rowViewportPosition(row)
            x = tw.columnViewportPosition(col)
            self._text_editor.move(parent.mapToGlobal(QPoint(x, y)))
            v = self._text_editor.open(value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                self._table.write(row, col, v)
            return None
        if ctype == "DATE":
            y = tw.rowViewportPosition(row)
            x = tw.columnViewportPosition(col)
            self._calendar.move(parent.mapToGlobal(QPoint(x, y)))
            v = self._calendar.open(value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                self._table.write(row, col, v)
            return None
#TODO: other types?
        e = self._editor
        e.setParent(parent)
        e.setText(value)
        if ctype == "GRADE":
            e.setValidator(self._grade_validator)
        else:
            e.setValidator(0)
        return e

    def setEditorData(self, editor, index):
        """Reimplement <setEditorData> to do nothing because the value is
        set in <createEditor>.
        """
        pass
        print("§setEditorData ... or, rather, not!")

    def destroyEditor(self, editor,  index):
        """Reimplement <destroyEditor> to do nothing because the editors
        are retained.
        """
        pass
        print("§destroyEditor ... or, rather, not!")

    def setModelData(self, editor, model, index):
        """Reimplement to write to back-end data table.
        """
        print("§setModelData:", index.row(), index.column(), editor.text())
        self._table.write(index.row(), index.column(), editor.text())

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

    def setup(self):
        """Call this when initializing a table for a new group.
        """
        glist = self._table.get_grade_list()
        self._min_grade_width = self._max_width(glist) + self._m_width
        self._grade_validator = ListValidator(glist)
        tw = self.parent() # the table widget, NOT the same as <parent>!
        for i in range(tw.columnCount()):
            dci = self._table.get_column_info(i)
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
        delegate = GradeTableDelegate(table_widget = tw, data_proxy = self)
        tw.setItemDelegate(delegate)
        self.event_filter = CopyPasteEventFilter(self)
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
        # This timer is to delay writing to database of changed grade-map
        # entries. The aim of this delay is so that when multiple changes
        # are made to one entry these will be collected before doing the
        # actual writing.
        self._pending_changes = {}
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self.update_db)

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

    ### grade-table "proxy" ###

    def get_grade_list(self) -> list[str]:
        return list(self.grade_table.grade_map)

    def get_column_info(self, col: int) -> DelegateColumnInfo:
        return self.grade_table.column_info[col]

    def read(self, row: int, col: int, copy_internal: bool = True) -> str:
        if copy_internal:
            return self.grade_table.read(row, col)
        else:
            return self.ui.grade_table.item(row, col).text()

    def write(self, row: int, col: int, val: str) -> bool:
        print("§CHANGED:", row, col, val)
        # Set data in underlying table
        dci = self.get_column_info(col)
        bad_field = dci.validate(val, write = True)
        if bad_field:
            REPORT_ERROR(T("WRITE_VALUE_ERROR",
                row = row + 1,
                col = bad_field,
                value = val
            ))
            return False
        self.grade_table.write(row, col, val)
        # Set cell in gui table
        self.display_cell(row, col, val)
        # Trigger row calculation with database update
        try:
            self._pending_changes[row][col] = val
        except KeyError:
            self._pending_changes[row] = {col: val}
        # If the timer is already running, this will stop and restart it
        self._timer.start(UPDATE_PAUSE)
        return True

    # Needed for the copy-paste facility
    def installEventFilter(self, eventfilter):
        self.ui.grade_table.installEventFilter(eventfilter)

    # Needed for the copy-paste facility
    def selectedRanges(self):
        return self.ui.grade_table.selectedRanges()

    ### actions ###

    def display_cell(self, row: int, col: int, val: str):
        print("TODO: display_cell")
        dci = self.get_column_info(col)
        v = self.get_display_value(val, dci)
        item = self.ui.grade_table.item(row, col)
        item.setText(v)

    def get_display_value(self, val, dci) -> str:
        if dci.TYPE == "DATE" and val:
            return print_date(val, trap = False) or "???"
        elif dci.validate(val):
            return "??"
        return val

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
        # Check that there are no pending database updates for grades
        for r, cd in self._pending_changes.items():
            if cd:
                REPORT_ERROR("TODO: pending changes not saved")
                break
        self._pending_changes = {}
        self.grade_table = (grade_table := GradeTable(
            self.occasion, self.class_group, self.report_info
        ))
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
        tw.itemDelegate().setup()
        ## Fill the grade table
        for i, gtline in enumerate(grade_table.lines):
            values = gtline.values
            # Add grades, etc.
            for j, dci in enumerate(grade_table.column_info):
                v = self.get_display_value(values[j], dci)
                item = QTableWidgetItem(v)
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
        for c, v in self.grade_table.calculate_row(r).items():
            # Write to display table
            self.display_cell(r, c, v)
        self._pending_changes[r] = {}
        self._timer.start(0)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from ui.ui_base import run
    _db = get_database()

    widget = ManageGradesPage()
    widget.enter()
    widget.ui.resize(1000, 550)
    run(widget.ui)
