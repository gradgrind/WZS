"""
ui/modules/grades_manager.py

Last updated:  2024-02-14

Front-end for managing grade reports.

#TODO:
    - editor for occasion/group lists

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

from ui.ui_base import (
    #load_ui,
    get_ui,
    ### QtWidgets:
    QTableWidget,
    QTableWidgetItem,
    QStyledItemDelegate,
    QLineEdit,
    ### QtGui:
    QColor,
    QValidator,
    ### QtCore:
    QObject,
    Qt,
    QTimer,
    Slot,
    QPoint,
    ### other
#    APP,
#    SHOW_CONFIRM,
    OPEN_FILE,
    SAVE_FILE,
    PROCESS,
)
from ui.rotated_table_header import RotatedHeaderView
from ui.table_support import (
    CopyPasteEventFilter,
    Calendar,
    TextEditor,
    ListChoice,
)
from ui.dialogs.dialog_edit_grade_table_selection \
    import editGradeTableSelectionDialog
from core.base import (
    DATAPATH,
    REPORT_INFO,
    REPORT_ERROR,
    REPORT_CRITICAL,
)
from core.basic_data import get_database, CONFIG, CALENDAR
from core.dates import print_date
from core.list_activities import class_report_data
from grades.grade_tables import GradeTable, DelegateColumnInfo
from grades.ods_template import BuildGradeTable, inputGradeTable
from grades.odt_grade_reports import make_grade_reports
from grades.odf_support import libre_office, merge_pdf

UPDATE_PAUSE = 1000     # time between cell edit and db update in ms

### -----


class GradeTableDelegate(QStyledItemDelegate):
    """Base class for table delegates using <DelegateColumnInfo> instances
    to determine behaviour. It handles the cell types relevant for the
    grades manager.
    The handling of the underlying data is done by the object passed as
    <data_proxy>.
    """
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

    def setup(self, grade_list: list[str]):
        """This is specific to a table with grades.
        Call this when initializing the table for a new group, or at least
        when the valid grades change.
        If using the delegate for another table, this can be overridden
        or ignored. That could, however, cause the attributes which are
        set here to remain unset, which will cause problems if there
        should be any grade cells in the table.
        """
        self._min_grade_width = self._max_width(grade_list) + self._m_width
        self._grade_validator = ListValidator(grade_list)

    def write_cell(self, row: int, col: int, val: str):
        """Use this to manage setting table values. It allows the
        cell value to be displayed in a customized manner.
        """
        dci = self._table.get_dci(row, col)
        if dci.TYPE == "DATE" and val:
            val = print_date(val, trap = False) or "???"
        elif dci.validate(val):
            val = "??"
        self.parent().item(row, col).setText(val)

    def createEditor(self, parent, option, index):
        row, col = index.row(), index.column()
        dci = self._table.get_dci(row, col)
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
            v = self._list_choice.open(dci.DATA["__ITEMS__"], value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                self._table.write_dp(row, col, v)
            return None
        if ctype == "TEXT":
            y = tw.rowViewportPosition(row)
            x = tw.columnViewportPosition(col)
            self._text_editor.move(parent.mapToGlobal(QPoint(x, y)))
            v = self._text_editor.open(value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                self._table.write_dp(row, col, v)
            return None
        if ctype == "DATE":
            y = tw.rowViewportPosition(row)
            x = tw.columnViewportPosition(col)
            self._calendar.move(parent.mapToGlobal(QPoint(x, y)))
            v = self._calendar.open(value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                self._table.write_dp(row, col, v)
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
        #print("§setEditorData ... or, rather, not!")

    def destroyEditor(self, editor,  index):
        """Reimplement <destroyEditor> to do nothing because the editors
        are retained.
        """
        pass
        #print("§destroyEditor ... or, rather, not!")

    def setModelData(self, editor, model, index):
        """Reimplement to write to back-end data table.
        """
        # The "editor" must be an object whose value is available via
        # the "text" method – like a QLineEdit.
        print("§setModelData:", index.row(), index.column(), editor.text())
        self._table.write_dp(index.row(), index.column(), editor.text())

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
            choices = dci.DATA["__ITEMS__"]
            return self._max_width(choices) + self._m_width * 2
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


class GroupDataProxy(QObject):
    def __init__(self, table_widget: QTableWidget, grade_table_proxy):
        super().__init__()
        self.table = table_widget
        self.grade_table_proxy = grade_table_proxy

    def get_dci(self, row, col) -> DelegateColumnInfo:
        """This provides the <DelegateColumnInfo> instance relevant for
        the given cell.
        """
        assert col == 0
        return self.dci_list[row]

    def set_data(self, dci_list: list[DelegateColumnInfo]):
        self.dci_list = dci_list
        self.table.clear()
        self.table.setRowCount(len(dci_list))
        self.table.setVerticalHeaderLabels(
            [dci.LOCAL for dci in dci_list]
        )
        delegate = self.table.itemDelegate()
        for r in range(len(dci_list)):
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 0, item)
            delegate.write_cell(r, 0, self.read(r, 0))

    def read(self, row: int, col: int, copy_internal: bool = True) -> str:
        assert col == 0
        if copy_internal:
            return self.dci_list[row].DATA.get("default") or ""
        else:
            return self.table.item(row, col).text()

    def write(self, row: int, col: int, val: str) -> bool:
        return self.write_dp(row, col, val)

    def write_dp(self, row: int, col: int, val: str) -> bool:
        """Write to a group data field, and thus also (potentially) to the
        corresponding grade table cells.
        """
        assert col == 0
        dci = self.dci_list[row]
        print("§CHANGED group-data:", row, col, val, dci)
        # Set data in underlying table
        bad_field = dci.validate(val, write = True)
        if bad_field:
            REPORT_ERROR(T("WRITE_GROUP_VALUE_ERROR",
                field = bad_field,
                value = val
            ))
            return False
        # Set cell in gui table
        self.table.itemDelegate().write_cell(row, col, val)
        # Update related items, including database
        val0 = dci.DATA.get("default") or ""
        dci.DATA["default"] = val
        if val != val0:
            if "C" in dci.FLAGS:
                # This is a calendar field, update it there
                CALENDAR.update(dci.DATA["calendar_key"], val)
            try:
                col = dci.DATA["column"]
            except KeyError:
                pass
            else:
                self.grade_table_proxy.update_col(col, val, val0)
        return True


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
        super().__init__()
        self._colours = {}
        #self.ui = load_ui("grades.ui", parent, self)
        self.ui = get_ui("grades.ui", parent, self)
        # group-data table
        dtw = self.ui.date_table
        self.group_data_proxy = GroupDataProxy(dtw, self)
        dtw.setItemDelegate(GradeTableDelegate(
            table_widget = dtw, data_proxy = self.group_data_proxy
        ))
        # grade-table
        tw = self.ui.grade_table
        self._delegate = GradeTableDelegate(
            table_widget = tw, data_proxy = self
        )
        tw.setItemDelegate(self._delegate)
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
        self.occasion = None
        self.class_group = None
        self.clear_display()
        self.db = get_database()
        self.report_info = class_report_data(GRADES = True)
        self.setup()

    def setup(self):
        ## Set up widgets
        self.suppress_handlers = True
        # Set up the "occasions" choice.
        grc = self.db.table("GRADE_REPORT_CONFIG")._template_info
        self.occasions = []
        i = -1
        for j, o in enumerate(sorted(grc)):
            _gl = sorted(grc[o], reverse = True)
            self.occasions.append((o, _gl))
            if o == self.occasion:
                i = j
                self._groups = _gl
        self.ui.combo_occasion.clear()
        self.ui.combo_occasion.addItems(p[0] for p in self.occasions)
        self.ui.combo_occasion.setCurrentIndex(i)
        self.fill_group_list()
        # Activate the window
        if self.occasion and self.class_group:
            self.set_group(self.class_group)
        self.suppress_handlers = False

    def clear_display(self):
        self.ui.grade_info.clear()
        self.ui.date_table.setRowCount(0)
        self.ui.frame_r.setDisabled(True)
        self.ui.grade_table.setDisabled(True)
        self.ui.grade_table.setRowCount(0)
        self.ui.grade_table.setColumnCount(0)

    ### grade-table "proxy" ###

    def get_dci(self, row, col) -> DelegateColumnInfo:
        """This provides the <DelegateColumnInfo> instance relevant for
        the given cell.
        """
        return self.grade_table.column_info[col]

    def read(self, row: int, col: int, copy_internal: bool = True) -> str:
        if copy_internal:
            return self.grade_table.read(row, col)
        else:
            return self.ui.grade_table.item(row, col).text()

    def write(self, row: int, col: int, val: str) -> bool:
        return self.write_dp(row, col, val)

#TODO: Why have I used "write_dp" instead of "write" in this module?
# "write" is used in pasting, so I need that too!
    def write_dp(self, row: int, col: int, val: str) -> bool:
        #print("§CHANGED:", row, col, val)
        # Set data in underlying table
        dci = self.get_dci(row, col)
        bad_field = dci.validate(val, write = True)
        if bad_field:
            REPORT_ERROR(T("WRITE_VALUE_ERROR",
                row = row + 1,
                col = bad_field,
                value = val
            ))
            return False
        self.grade_table.write_gt(row, col, val)
        # Set cell in gui table
        self._delegate.write_cell(row, col, val)
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

    def update_col(self, col: int, val: str, val0: str):
        r_changes = self.grade_table.update_all(col, val, val0)
        for r, changes in r_changes:
            for c, v in changes.items():
                self._delegate.write_cell(r, c, v)
        self.set_modified()

    ### actions ###

    def set_modified(self):
        self.ui.last_modified.setText(self.grade_table.modified)

    def fill_group_list(self):
        self.ui.combo_group.clear()
        i = self.ui.combo_occasion.currentIndex()
        if i < 0: return
        olist = self.occasions[i][1]
        self.ui.combo_group.addItems(olist)
        if len(olist) > 1:
            if self.class_group:
                self.ui.combo_group.setCurrentText(self.class_group)
            else:
                self.ui.combo_group.setCurrentIndex(-1)
        elif olist:
            self.ui.combo_group.setCurrentIndex(0)

    def set_group(self, class_group):
        self.suppress_handlers = True
        self.class_group = class_group
        tw = self.ui.grade_table
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
            if "*" in dci.FLAGS:
                # Add to group-data table
                dci.DATA["column"] = len(headers)
                dtdata.append(dci)
            headers.append(dci.LOCAL)
        ## Show grade info
        self.ui.grade_info.setMarkdown(
            getattr(CONFIG, f"GRADE_INFO_{self.grade_table.grade_scale}")
        )
        ## Initialize group-data table
        self.group_data_proxy.set_data(dtdata)
        ## Initialize grade table
        tw.clear()
        tw.setColumnCount(len(headers))
        vheaders = [gtline.student_name for gtline in grade_table.lines]
        tw.setRowCount(len(vheaders))
        tw.setHorizontalHeaderLabels(headers)
        tw.setVerticalHeaderLabels(vheaders)
        ## Set up the grade table ...
        self._delegate.setup(list(self.grade_table.grade_map))
        # First the column widths
        for c, dci in enumerate(grade_table.column_info):
            w = self._delegate._column_width(dci)
            if w >= 0:
                tw.setColumnWidth(c, w)
                tw.showColumn(c)
            else:
                tw.hideColumn(c)
        # Now the individual cells
        for r, gtline in enumerate(grade_table.lines):
            values = gtline.values
            # Add grades, etc.
            for c, dci in enumerate(grade_table.column_info):
                item = QTableWidgetItem()
                item.setBackground(self.colour_cache(dci.COLOUR))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tw.setItem(r, c, item)
                self._delegate.write_cell(r, c, values[c])
        self.suppress_handlers = False
        self.ui.frame_r.setDisabled(False)
        self.ui.grade_table.setDisabled(False)
        self.set_modified()
#TODO: This is a fix for a visibility problem (gui refresh)
#        for w in APP.topLevelWindows():
#            if w.isVisible():
#                w.show()

    def save_grade_table(self, with_grades: bool):
        gt = BuildGradeTable(
            self.occasion,
            self.class_group,
            with_grades = with_grades
        )
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

    def make_reports(self, show_output: bool):
        """This is a lengthy process which should be run in a "PROCESS".
        """
        # Set paths. If necessary, create folders
        outdir = DATAPATH(
            f"{self.occasion}/{self.class_group}".replace(" ", "_"),
            "working_data"
        )
        #print("§outdir", outdir)
        pdf_dir = os.path.join(outdir, "pdf")
        os.makedirs(pdf_dir, exist_ok = True)
        # Create odt files
        odt_lists = {}
        REPORT_INFO(T("MAKE_ODT"))
        for odt, sname, ttype in make_grade_reports(
            self.occasion, self.class_group
        ):
            outpath = os.path.join(outdir, sname) + ".odt"
            with open(outpath, 'bw') as fh:
                fh.write(odt)
            REPORT_INFO(f" --> ({ttype}) {outpath}")
            try:
                odt_lists[ttype].append(outpath)
            except KeyError:
                odt_lists[ttype] = [outpath]
        # Clear pdf folder
        for f in os.listdir(pdf_dir):
            os.remove(os.path.join(pdf_dir, f))
        # Convert odt files to pdf
        pdf_paths = []
        for ttype, odt_list in odt_lists.items():
            REPORT_INFO(T("MAKE_PDF", n = len(odt_list), rtype = ttype))
            libre_office(odt_list, pdf_dir, show_output = show_output)
            pdf_list = []
            for f in odt_list:
                f0 = os.path.basename(f).rsplit('.', 1)[0]
                f1 = os.path.join(pdf_dir, f"{f0}.pdf")
                if not os.path.isfile(f1):
                    REPORT_ERROR(T("PDF_GEN_FAILED", fname = f0))
                    continue
                pdf_list.append(f1)
            # Merge the resulting files to a single pdf
            if not pdf_list:
                continue
            REPORT_INFO(T("MERGE_REPORTS", n = len(pdf_list), rtype = ttype))
            pdfname = T("GRADE_REPORT",
                occasion = self.occasion.replace(" ", "_"),
                group = self.class_group,
                rtype = ttype,
            )
            pdf_path = SAVE_FILE(
                f'{T("pdf_file")} (*.pdf)',
                start = f"{pdfname}.pdf",
                title = T("SAVE_REPORTS", rtype = ttype),
            )
            if not pdf_path:
                continue
            if not pdf_path.endswith(".pdf"):
                pdf_path += ".pdf"
            merge_pdf(pdf_list, pdf_path)
            pdf_paths.append(pdf_path)
        for p in pdf_paths:
            REPORT_INFO(T("SAVED_REPORTS", path = p))

    ### slots ###

    @Slot()
    def on_edit_groups_clicked(self):
        res = editGradeTableSelectionDialog(
            self.occasion,
            self.class_group,
            parent = self.ui.edit_groups,
        )
        if res:
            self.occasion, self.class_group = res
        self.setup()

    @Slot(int)
    def on_combo_occasion_currentIndexChanged(self, i):
        if self.suppress_handlers: return
        self.suppress_handlers = True
        self.fill_group_list()
        self.occasion, self._groups = self.occasions[i]
        #print("§SET occasion:", self.occasion)
        self.suppress_handlers = False
        i = self.ui.combo_group.currentIndex()
        if i >= 0:
            self.set_group(self._groups[i])
        else:
            self.clear_display()

    @Slot(int)
    def on_combo_group_currentIndexChanged(self, i):
        if self.suppress_handlers: return
        self.set_group(self._groups[i])

    @Slot()
    def on_pb_grade_input_table_clicked(self):
        self.save_grade_table(with_grades = False)

    @Slot()
    def on_pb_make_grade_table_clicked(self):
        self.save_grade_table(with_grades = True)

    @Slot()
    def on_pb_read_grade_table_clicked(self):
        fpath = OPEN_FILE(
            f'{T("ods_file")} (*.ods)',
            #start = ?,
            title = T("GET_GRADE_TABLE"),
        )
        if fpath:
            r_changes = inputGradeTable(fpath, self.grade_table)
            for r, changes in r_changes:
                for c, v in changes.items():
                    self._delegate.write_cell(r, c, v)

    @Slot()
    def on_pb_make_reports_clicked(self):
        PROCESS(
            self.make_reports,
            title = T("MAKE_REPORTS"),
            show_output = self.ui.cb_extra_info.isChecked()
        )

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
            self._delegate.write_cell(r, c, v)
        self.set_modified()
        self._pending_changes[r] = {}
        self._timer.start(0)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from ui.ui_base import run
    _db = get_database()

    widget = ManageGradesPage()
    widget.enter()
    widget.ui.resize(0, 0)
    run(widget.ui)
