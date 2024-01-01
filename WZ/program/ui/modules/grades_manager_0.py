"""
ui/modules/grades_manager.py

Last updated:  2023-07-06

Front-end for managing grade reports.


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

##### Configuration #####################
# Some sizes in points
GRADETABLE_TITLEHEIGHT = 40
GRADETABLE_FOOTERHEIGHT = 30
GRADETABLE_ROWHEIGHT = 25
GRADETABLE_SUBJECTWIDTH = 25
GRADETABLE_EXTRAWIDTH = 40
GRADETABLE_HEADERHEIGHT = 100
GRADETABLE_PUPILWIDTH = 200
GRADETABLE_LEVELWIDTH = 50

COMPONENT_COLOUR = "ffeeff"
COMPOSITE_COLOUR = "eeffff"
CALCULATED_COLOUR = "ffffcc"

#########################################

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import start
    from ui.ui_base import StandalonePage as Page

    #    start.setup(os.path.join(basedir, 'TESTDATA'))
    start.setup(os.path.join(basedir, "DATA-2023"))
else:
    from ui.ui_base import StackPage as Page

T = TRANSLATIONS("ui.modules.grades_manager")

### +++++

from core.db_access import open_database, db_values
from core.base import class_group_split, Dates
from core.basic_data import check_group
from core.pupils import pupils_in_group, pupil_name
from grades.grades_base import (
    GetGradeConfig,
    MakeGradeTable,
    FullGradeTable,
    FullGradeTableUpdate,
    UpdatePupilGrades,
    UpdateTableInfo,
    LoadFromFile,
    NO_GRADE,
)
from grades.make_grade_reports import MakeGroupReports, report_name

from ui.ui_base import (
    QWidget,
    QFormLayout,
    QDialog,
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGroupBox,
    # QtCore
    Qt,
    QDate,
    Signal,
    # Other
    HLine,
    run,
    date2qt,
)
from ui.grid_base import GridViewAuto
from ui.cell_editors import (
    CellEditorTable,
    CellEditorText,
    CellEditorDate,
)

### -----


def init():
    MAIN_WIDGET.add_tab(ManageGrades())


class ManageGrades(Page):
    name = T["MODULE_NAME"]
    title = T["MODULE_TITLE"]

    def __init__(self):
        super().__init__()
        self.grade_manager = GradeManager()
        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addWidget(self.grade_manager)

    def enter(self):
        open_database()
        self.grade_manager.init_data()

    def is_modified(self):
        """Return <True> if there are unsaved changes.
        This module always saves changes immediately.
        """
        return False


# ++++++++++++++ The widget implementation ++++++++++++++


class InstanceSelector(QWidget):
    def __init__(self):
        super().__init__()
        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(0, 0, 0, 0)
        self.combobox = QComboBox()
        hbox.addWidget(self.combobox)
        label = "+"
        self.addnew = QPushButton(label)
        self.addnew.setToolTip("New Item")
        width = self.addnew.fontMetrics().boundingRect(label).width() + 16
        self.addnew.setMaximumWidth(width)
        hbox.addWidget(self.addnew)
        self.addnew.clicked.connect(self.do_addnew)

    # TODO: According to the "occasion" and class-group there can be different
    # sorts of "instance". The main report types don't cater for "instances",
    # so the combobox and button could be disabled. Where a list is supplied
    # in the configuration, no new values are possible, the current value
    # would come from the database entry. Perhaps dates might be permitted.
    # In that case a date-choice widget would be appropriate.
    # Single report types, and maybe some other types, would take any string.
    # In that case a line editor could be used.

    def do_addnew(self):
        InstanceDialog.popup(
            pos=self.mapToGlobal(self.rect().bottomLeft())
        )

    def set_list(self, value_list: list[str], mutable: int):
        self.value_list = value_list
        self.combobox.clear()
        self.combobox.addItems(value_list)
        self.setEnabled(mutable >= 0)
        self.addnew.setEnabled(mutable > 0)

    def text(self):
        return self.combobox.currentText()


# TODO
class InstanceDialog(QDialog):
    @classmethod
    def popup(cls, start_value="", parent=None, pos=None):
        d = cls(parent)
        #        d.init()
        if pos:
            d.move(pos)
        return d.activate(start_value)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # self.setWindowFlags(Qt.WindowType.Popup)
        vbox0 = QVBoxLayout(self)
        vbox0.setContentsMargins(0, 0, 0, 0)
        # vbox0.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.ledit = QLineEdit()
        vbox0.addWidget(self.ledit)

    def activate(self, start_value):
        self.result = None
        self.ledit.setText(start_value)
        self.exec()
        print("DONE", self.result)
        return self.result


class GradeManager(QWidget):
    def __init__(self):
        super().__init__()
        hbox = QHBoxLayout(self)
        vboxl = QVBoxLayout()
        hbox.addLayout(vboxl)
        vboxr = QVBoxLayout()
        hbox.addLayout(vboxr)
        hbox.setStretchFactor(vboxl, 1)

        # The class data table
        self.pupil_data_table = GradeTableView()
        #        EdiTableWidget()
        vboxl.addWidget(self.pupil_data_table)
        self.pupil_data_table.signal_modified.connect(self.updated)

        # Various "controls" in the panel on the right
        grade_config = GetGradeConfig()
        self.info_fields = dict(grade_config["INFO_FIELDS"])
        formbox = QFormLayout()
        vboxr.addLayout(formbox)
        self.occasion_selector = QComboBox()
        self.occasion_selector.currentTextChanged.connect(self.changed_occasion)
        formbox.addRow(self.info_fields["OCCASION"], self.occasion_selector)
        self.class_selector = QComboBox()
        self.class_selector.currentTextChanged.connect(self.changed_class)
        formbox.addRow(self.info_fields["CLASS_GROUP"], self.class_selector)
        #        self.instance_selector = QComboBox()
        self.instance_selector = InstanceSelector()
        #        delegate = InstanceDelegate(self)
        #        self.instance_selector.setEditable(True)
        #        self.instance_selector.setItemDelegate(delegate)
        #        self.instance_selector.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # TODO: ? Rather index changed signal?
        #        self.instance_selector.currentTextChanged.connect(self.select_instance)
        formbox.addRow(self.info_fields["INSTANCE"], self.instance_selector)

        # Date fields
        firstday = QDate.fromString(
            CALENDAR["FIRST_DAY"], Qt.DateFormat.ISODate
        )
        lastday = QDate.fromString(CALENDAR["LAST_DAY"], Qt.DateFormat.ISODate)
        self.issue_date = QDateEdit()
        self.issue_date.setMinimumDate(firstday)
        self.issue_date.setMaximumDate(lastday)
        self.issue_date.setCalendarPopup(True)
        date_format = date2qt(CONFIG["DATEFORMAT"])
        self.issue_date.setDisplayFormat(date_format)
        formbox.addRow(self.info_fields["DATE_ISSUE"], self.issue_date)
        self.issue_date.dateChanged.connect(self.issue_date_changed)
        self.grade_date = QDateEdit()
        self.grade_date.setMinimumDate(firstday)
        self.grade_date.setMaximumDate(lastday)
        self.grade_date.setCalendarPopup(True)
        self.grade_date.setDisplayFormat(date_format)
        formbox.addRow(self.info_fields["DATE_GRADES"], self.grade_date)
        self.grade_date.dateChanged.connect(self.grade_date_changed)
        self.modified_time = QLineEdit()
        self.modified_time.setReadOnly(True)
        formbox.addRow(self.info_fields["MODIFIED"], self.modified_time)

        # vboxr.addWidget(HLine())

        # vboxr.addWidget(QLabel(T["Pupils"]))
        # self.pupil_list = QListWidget()
        # self.pupil_list.setSelectionMode(
        #    QAbstractItemView.SelectionMode.SingleSelection
        # )
        # vboxr.addWidget(self.pupil_list)

        vboxr.addStretch()
        make_pdf = QPushButton(T["Export_PDF"])
        make_pdf.clicked.connect(self.pupil_data_table.export_pdf)
        vboxr.addWidget(make_pdf)
        vboxr.addSpacing(20)

        # TODO: read input tables,
        # generate reports using only selected pupils? - what about
        # multiple selection? pop up a checklist?

        make_input_table = QPushButton(T["MAKE_INPUT_TABLE"])
        make_input_table.clicked.connect(self.do_make_input_table)
        vboxr.addWidget(make_input_table)
        vboxr.addSpacing(20)

        read_input_table = QPushButton(T["READ_INPUT_TABLE"])
        read_input_table.clicked.connect(self.do_read_input_table)
        vboxr.addWidget(read_input_table)
        vboxr.addSpacing(20)

        vboxr.addStretch()
        # vboxr.addWidget(HLine())
        self.make_reports = QGroupBox(T["MAKE_REPORTS"])
        vboxr.addWidget(self.make_reports)
        gblayout = QVBoxLayout(self.make_reports)
        self.show_data = QCheckBox(T["SHOW_DATA"])
        self.show_data.setCheckState(Qt.CheckState.Unchecked)
        gblayout.addWidget(self.show_data)
        pb_make_reports = QPushButton(T["DO_MAKE_REPORTS"])
        pb_make_reports.clicked.connect(self.do_make_reports)
        gblayout.addWidget(pb_make_reports)

    def init_data(self):
        self.suppress_callbacks = True
        # Set up "occasions" here, from config
        self.occasion_selector.clear()
        ### The configuration data should be based first on the "occasion",
        ### then the group – the other way round from in the config file.
        self.occasion2data = {}
        for g, infolist in GetGradeConfig()["GROUP_DATA"].items():
            for o, data in infolist:
                try:
                    self.occasion2data[o][g] = data
                except KeyError:
                    self.occasion2data[o] = {g: data}
                    self.occasion_selector.addItem(o)
        # Enable callbacks
        self.suppress_callbacks = False
        self.class_group = None
        self.changed_occasion(self.occasion_selector.currentText())

    def updated(self, timestamp):
        self.modified_time.setText(timestamp)

    def changed_occasion(self, new_occasion: str):
        if self.suppress_callbacks:
            return
        print("NEW OCCASION:", new_occasion)
        # A change of occasion should preserve the class-group, if this
        # class-group is also available for the new occasion.
        self.occasion = new_occasion
        self.occasion_data = self.occasion2data[self.occasion]
        groups = []
        for g in self.occasion_data:
            if g[0] == "_":
                # Keys starting with '_' are for additional, non-group
                # related information.
                continue
            klass, group = class_group_split(g)
            if not check_group(klass, group):
                REPORT(
                    "ERROR",
                    T["BAD_GROUP_IN_CONFIG"].format(
                        group=g, occasion=new_occasion
                    ),
                )
                continue
            groups.append(g)
        groups.sort(reverse=True)
        self.suppress_callbacks = True
        self.class_selector.clear()
        self.class_selector.addItems(groups)
        self.class_selector.setCurrentText(self.class_group)  # no exception
        # Enable callbacks
        self.suppress_callbacks = False
        self.changed_class(self.class_selector.currentText())

    def changed_class(self, new_class_group):
        if self.suppress_callbacks:
            print("Class change handling disabled:", new_class_group)
            return
        print("NEW GROUP:", new_class_group)
        #        grade_table = self.get_grade_table(occasion, class_group)

        self.class_group = new_class_group
        self.group_data = self.occasion_data[new_class_group]

#TODO: Is this used anywhere??? It has the corret order, unlike what appears
# on the screen ...
#        self.pupil_data_list = pupils_in_group(new_class_group, date=None)

        # self.pupil_list.clear()
        # self.pupil_list.addItems([pupil_name(p) for p in self.pupil_data_list])

        self.suppress_callbacks = True
        try:
            instance_data = self.group_data["INSTANCE"]
        except KeyError:
            # No instances are allowed
            self.instance_selector.set_list([], -1)
        else:
            if isinstance(instance_data, list):
                self.instance_selector.set_list(instance_data, 0)
            else:
                # Get items from database
                instances = db_values(
                    "GRADES_INFO",
                    "INSTANCE",
                    sort_field="INSTANCE",
                    CLASS_GROUP=self.class_group,
                    OCCASION=self.occasion,
                )
                self.instance_selector.set_list(instances, 1)
        self.suppress_callbacks = False
        self.select_instance()

    def select_instance(self, instance=""):
        #
        print(f"TODO: Instance '{instance}' // {self.instance_selector.text()}")

        __instance = self.instance_selector.text()
        if instance:
            if __instance != instance:
                raise Bug(f"Instance mismatch: '{instance}' vs. '{__instance}'")
        else:
            instance = __instance
        grade_table = FullGradeTable(
            self.occasion, self.class_group, instance
        )
        try:
            grade_table["COLUMNS"]["INPUT"].get("REPORT_TYPE")
            self.make_reports.setEnabled(True)
        except KeyError:
            try:
                grade_table["COLUMNS"]["CALCULATE"].get("REPORT_TYPE")
                self.make_reports.setEnabled(True)
            except KeyError:
                self.make_reports.setEnabled(False)
        self.instance = instance
        self.suppress_callbacks = True
        self.issue_date.setDate(
            QDate.fromString(grade_table["DATE_ISSUE"], Qt.DateFormat.ISODate)
        )
        self.grade_date.setDate(
            QDate.fromString(grade_table["DATE_GRADES"], Qt.DateFormat.ISODate)
        )
        self.suppress_callbacks = False
        self.pupil_data_table.setup(grade_table)
        # Update if the stored dates needed adjustment to fit in range
        self.grade_date_changed(self.grade_date.date())
        self.issue_date_changed(self.issue_date.date())
        # Ensure that the "last modified" field is set
        self.updated(grade_table["MODIFIED"])

    def issue_date_changed(self, qdate):
        if self.suppress_callbacks:
            return
        new_date = qdate.toString(Qt.DateFormat.ISODate)
        if new_date != self.pupil_data_table.grade_table["DATE_ISSUE"]:
            timestamp = UpdateTableInfo(
                self.pupil_data_table.grade_table,
                "DATE_ISSUE",
                new_date,
            )
            self.updated(timestamp)
            # TODO: Reload table? ... shouldn't be necessary
            # self.select_instance()

    def grade_date_changed(self, qdate):
        if self.suppress_callbacks:
            return
        new_date = qdate.toString(Qt.DateFormat.ISODate)
        if new_date != self.pupil_data_table.grade_table["DATE_GRADES"]:
            timestamp = UpdateTableInfo(
                self.pupil_data_table.grade_table,
                "DATE_GRADES",
                new_date,
            )
            self.updated(timestamp)
            # Reload table
            self.select_instance()

    def do_make_input_table(self):
        table_data = self.pupil_data_table.grade_table
        xlsx_bytes = MakeGradeTable(table_data)
        fname = report_name(table_data, T["GRADES"]) + ".xlsx"
        fpath = SAVE_FILE("Excel-Datei (*.xlsx)", start=fname, title=None)
        if not fpath:
            return
        if not fpath.endswith(".xlsx"):
            fpath += ".xlsx"
        with open(fpath, 'wb') as fh:
            fh.write(xlsx_bytes)
        REPORT("INFO", f"Written to {fpath}")

    def do_read_input_table(self):
        if Dates.today() > self.pupil_data_table.grade_table["DATE_GRADES"]:
            SHOW_ERROR("Data after closing date")
            return
        path = OPEN_FILE("Tabelle (*.xlsx *.ods *.tsv)")
        if not path:
            return
        pid2grades = LoadFromFile(
            filepath=path,
            OCCASION=self.occasion,
            CLASS_GROUP=self.class_group,
            INSTANCE=self.instance,
        )
        grade_table = FullGradeTable(
            occasion=self.occasion,
            class_group=self.class_group,
            instance=self.instance,
        )
        FullGradeTableUpdate(grade_table, pid2grades)
        self.pupil_data_table.setup(grade_table)
        self.updated(grade_table["MODIFIED"])

    def do_make_reports(self):
        mgr = MakeGroupReports(self.pupil_data_table.grade_table)
        rtypes = mgr.split_report_types()
        for rtype in rtypes:
            if rtype:
                PROCESS(
                    mgr.gen_files,
                    title=T["MAKE_REPORTS"],
                    rtype=rtype,
                    clean_folder=True,
                    show_data=self.show_data.isChecked()
                )
                fname = mgr.group_file_name()
#TODO: save dialog
                fpath = DATAPATH(f"GRADES/{fname}")
                mgr.join_pdfs(fpath)
                REPORT("INFO", f"Saved: {mgr.join_pdfs(fpath)}")


class GradeTableView(GridViewAuto):
    # class GradeTableView(GridView):
    signal_modified = Signal(str)

    def setup(self, grade_table):
        self.grade_table = grade_table
        pupils_list = grade_table["PUPIL_LIST"]
        grade_config_table = grade_table["GRADE_VALUES"]

        ### Collect column data
        col2colour = []     # allows colouring of the columns
        click_handler = []  # set the editor function for each column
        column_widths = []  # as it says ...
        column_headers = [] # [(sid, name),  ... ]
        # Customized "extra-field" widths
        custom_widths = GetGradeConfig().get("EXTRA_FIELD_WIDTHS")
        grade_click_handler = CellEditorTable(grade_config_table)
        date_click_handler = CellEditorDate(empty_ok=True)
        ## Deal with the column types separately
        # Collect column widths, colours, headers and click-handlers
        column_data = grade_table["COLUMNS"]
        for sdata in column_data["SUBJECT"]:
            column_headers.append((sdata["SID"], sdata["NAME"]))
            column_widths.append(GRADETABLE_SUBJECTWIDTH)
            if "COMPOSITE" in sdata:
                col2colour.append(COMPONENT_COLOUR)
                click_handler.append(grade_click_handler)
            else:
                col2colour.append(None)
                click_handler.append(grade_click_handler)
        for sdata in column_data["COMPOSITE"]:
            column_headers.append((sdata["SID"], sdata["NAME"]))
            column_widths.append(GRADETABLE_SUBJECTWIDTH)
            col2colour.append(COMPOSITE_COLOUR)
            click_handler.append(None)
        for sdata in column_data["CALCULATE"]:
            column_headers.append((sdata["SID"], sdata["NAME"]))
            try:
                column_widths.append(int(custom_widths[sdata["SID"]]))
            except KeyError:
                column_widths.append(GRADETABLE_EXTRAWIDTH)
            except ValueError:
                REPORT(
                    "ERROR",
                    T["BAD_CUSTOM_WIDTH"].format(
                        sid = sdata["SID"],
                        path=GetGradeConfig()["__PATH__"],
                    )
                )
                column_widths.append(GRADETABLE_EXTRAWIDTH)
            col2colour.append(CALCULATED_COLOUR)
            click_handler.append(None)
        for sdata in column_data["INPUT"]:
            column_headers.append((sdata["SID"], sdata["NAME"]))
            try:
                column_widths.append(int(custom_widths[sdata["SID"]]))
            except KeyError:
                column_widths.append(GRADETABLE_EXTRAWIDTH)
            except ValueError:
                REPORT(
                    "ERROR",
                    T["BAD_CUSTOM_WIDTH"].format(
                        sid = sdata["SID"],
                        path=GetGradeConfig()["__PATH__"],
                    )
                )
                column_widths.append(GRADETABLE_EXTRAWIDTH)
            method = sdata["METHOD"]
            parms = sdata["PARAMETERS"]
            if method == "CHOICE":
                values = [[[v], ""] for v in parms["CHOICES"]]
                editor = CellEditorTable(values)
            elif method == "CHOICE_MAP":
                values = [[[v], text] for v, text in parms["CHOICES"]]
                editor = CellEditorTable(values)
            elif method == "TEXT":
                editor = CellEditorText()
            elif method == "DATE":
                editor = date_click_handler
            else:
                REPORT(
                    "ERROR",
                    T["UNKNOWN_INPUT_METHOD"].format(
                        path=GetGradeConfig()["__PATH__"],
                        group=grade_table["CLASS_GROUP"],
                        occasion=grade_table["OCCASION"],
                        sid=sdata["SID"],
                        method=method
                    )
                )
                editor = None
            col2colour.append(None)
            click_handler.append(editor)
        __rows = (GRADETABLE_HEADERHEIGHT,) + (GRADETABLE_ROWHEIGHT,) * len(
            pupils_list
        )
        __cols = [
            GRADETABLE_PUPILWIDTH,
            GRADETABLE_LEVELWIDTH,
        ] + column_widths
        self.init(__rows, __cols)

        self.grid_line_thick_v(2)
        self.grid_line_thick_h(1)

        ### The column headers
        hheaders = dict(GetGradeConfig()["HEADERS"])
        self.get_cell((0, 0)).set_text(hheaders["PUPIL"])
        self.get_cell((0, 1)).set_text(hheaders["LEVEL"])
        colstart = 2
        self.col0 = colstart
        self.sid2col = {}
        for col, sn in enumerate(column_headers):
            gridcol = col + colstart
            self.sid2col[sn[0]] = gridcol
            cell = self.get_cell((0, gridcol))
            cell.set_verticaltext()
            cell.set_valign("b")
            cell.set_background(col2colour[col])
            cell.set_text(sn[1])

        ### The data rows
        rowstart = 1
        self.row0 = rowstart
        row = 0
        self.pid2row = {}
        for pdata, pgrades in pupils_list:
            gridrow = row + rowstart
            pid = pdata["PID"]
            self.pid2row[pid] = gridrow
            cell = self.get_cell((gridrow, 0))
            cell.set_halign("l")
            cell.set_text(pupil_name(pdata))
            cell = self.get_cell((gridrow, 1))
            cell.set_text(pdata["LEVEL"])

            for col, sn in enumerate(column_headers):
                cell = self.get_cell((gridrow, col + colstart))
                cell.set_background(col2colour[col])
                # ?
                # This is not taking possible value delegates into
                # account – which would allow the display of a text
                # distinct from the actual value of the cell.
                # At the moment it is not clear that I would need such
                # a thing, but it might be useful to have it built in
                # to the base functionality in base_grid.
                # For editor types CHOICE_MAP it might come in handy,
                # for instance ... though that is not quite the intended
                # use of CHOICE_MAP – the "key" is displayed, but it is
                # the "value" that is needed for further processing.
                # For this it would be enough to set the "VALUE" property.

                sid = sn[0]
                cell.set_property("PID", pid)
                cell.set_property("SID", sid)
                try:
                    cell.set_text(pgrades[sid])
                except KeyError:
                    cell.set_text(NO_GRADE)
                else:
                    if (handler := click_handler[col]):
                        cell.set_property("EDITOR", handler)
            row += 1

        self.rescale()

    def cell_modified(self, properties: dict):
        """Override base method in grid_base.GridView.
        A single cell is to be written.
        """
        new_value = properties["VALUE"]
        pid = properties["PID"]
        sid = properties["SID"]
        grades = self.grade_table["PUPIL_LIST"].get(pid)[1]
        grades[sid] = new_value
        # Update this pupil's grades (etc.) in the database
        changes, timestamp = UpdatePupilGrades(self.grade_table, pid)
        self.set_modified_time(timestamp)
        if changes:
            # Update changed display cells
#TODO--
            print("??? CHANGES", changes)
            row = self.pid2row[pid]
            for sid, oldval in changes:
                try:
                    col = self.sid2col[sid]
                except KeyError:
                    continue
                self.get_cell((row, col)).set_text(grades[sid])

#?
    def set_modified_time(self, timestamp):
#        self.grade_table["MODIFIED"] = timestamp
        # Signal change
        self.signal_modified.emit(timestamp)

    def write_to_row(self, row, col, values):
        """Write a list of values to a position (<col>) in a given row.
        This is called when pasting.
        """
        # Only write to cells when all are editable, and check the values!
# Maybe just skip non-writable cells?
        # Then do an UpdatePupilGrades ...
        prow = row - self.row0
        pupil_list = self.grade_table["PUPIL_LIST"]
        if prow < 0 or prow >= len(pupil_list):
            SHOW_ERROR(T["ROW_NOT_EDITABLE"])
            return
        for i in range(len(values)):
            cell = self.get_cell((row, col + i))
            try:
                editor = cell.get_property("EDITOR")
            except KeyError:
                SHOW_ERROR(T["CELL_NOT_EDITABLE"].format(
                    field=self.get_cell((0, col + i)).get_property("VALUE")
                ))
                return
            try:
                validator = editor.validator
            except AttributeError:
                pass
            else:
                if not validator(values[i]):
                    SHOW_ERROR(T["INVALID_VALUE"].format(
                        field=self.get_cell((0, col + i)).get_property("VALUE"),
                        val=values[i]
                    ))
                    return
        pdata, grades = pupil_list[prow]
        for i in range(len(values)):
            cell = self.get_cell((row, col + i))
            sid = cell.get_property("SID")
            grades[sid] = values[i]
        # Update this pupil's grades (etc.) in the database
        pid = pdata["PID"]
        changes, timestamp = UpdatePupilGrades(self.grade_table, pid)
        self.set_modified_time(timestamp)
        super().write_to_row(row, col, values)
        if changes:
            # Update changed display cells
            for sid, oldval in changes:
                self.get_cell((row, self.sid2col[sid])).set_text(grades[sid])

    def export_pdf(self, fpath=None):
        titleheight = self.pt2px(GRADETABLE_TITLEHEIGHT)
        footerheight = self.pt2px(GRADETABLE_FOOTERHEIGHT)
        info_fields = dict(GetGradeConfig()["INFO_FIELDS"])
        items = []
        cgroup = self.grade_table["CLASS_GROUP"]
        items.append(
            self.set_title(
                f'{info_fields["CLASS_GROUP"]}: {cgroup}',
                -titleheight // 2,
                font_scale=1.2,
                halign="l",
            )
        )
        occasion = self.grade_table["OCCASION"]
        instance = self.grade_table["INSTANCE"]
        if instance:
            occasion = f"{occasion}: {instance}"
        items.append(
            self.set_title(occasion, -titleheight // 2, halign="c")
        )
        items.append(
            self.set_title(
                self.grade_table["DATE_ISSUE"],
                -titleheight // 2,
                halign="r",
            )
        )
        items.append(
            self.set_title(
                f'{info_fields["DATE_GRADES"]}: {self.grade_table["DATE_GRADES"]}',
                footerheight // 2,
                halign="l",
            )
        )
        items.append(
            self.set_title(
                f'{info_fields["MODIFIED"]}: {self.grade_table["MODIFIED"]}',
                footerheight // 2,
                halign="r",
            )
        )
        if not fpath:
            fpath = SAVE_FILE(
                "pdf-Datei (*.pdf)",
                report_name(self.grade_table, T["GRADES"]) + ".pdf"
            )
            if not fpath:
                return
        if not fpath.endswith(".pdf"):
            fpath += ".pdf"
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        self.to_pdf(fpath, titleheight=titleheight, footerheight=footerheight)
        # grid.to_pdf(fpath, can_rotate = False, titleheight=titleheight, footerheight=footerheight)
        for item in items:
            self.delete_item(item)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    widget = ManageGrades()
    widget.enter()

    widget.resize(1000, 500)
    run(widget)
