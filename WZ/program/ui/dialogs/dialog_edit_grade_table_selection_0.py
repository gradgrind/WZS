"""
ui/dialogs/dialog_edit_grade_table_selection.py

Last updated:  2024-02-14

#TODO: When called from grades_manager the template pop-up is below the
# dialog window ...
# ~ l.459 by adding a parent it's okay again, but see the comment above
# that!

Supporting "dialog" for the grades manager – edit the "occasion" + group
pairs and their associated report types and templates.


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

import os
if __name__ == "__main__":
    import sys

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import Tr
T = Tr("ui.dialogs.dialog_edit_grade_table_selection")

### +++++

from typing import Optional

from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QStyledItemDelegate,
    QLineEdit,
    ### QtGui:
    ### QtCore:
    QPoint,
    Slot,
    QTimer,
    ### other
    get_ui_locals,
    SHOW_CONFIRM,
)
from ui.table_support import Table, ListChoice
from core.base import DATAPATH, REPORT_ERROR
from core.basic_data import get_database, CONFIG
from core.classes import format_class_group, class_group_split
import grades.grade_tables  # noqa (load table "GRADE_REPORT_CONFIG")

### -----


class ReportTable:
    def __init__(self, table: Table, update_report_type):
        self.table = table
        self._update = update_report_type
        self._delegate = TableDelegate(table.qtable, self)
        table.qtable.setItemDelegate(self._delegate)
        tdir = DATAPATH(CONFIG.GRADE_REPORT_TEMPLATES, "TEMPLATES")
        self._choices = [
            f[:-4] for f in sorted(os.listdir(tdir))
            if f.endswith('.odt')
        ]

    def setup(self, data):
        self.data = data
        n = len(data)
        assert n > 0
        # An empty line is only permissible as the only entry
        if n > 1 or data[0][0]:
            data.append(("", "", 0))    # add an empty line for a new entry
        self.table.set_row_count(len(data))
        r = 0
        for rtag, tfile, _ in data:
            self.table.write(r, 0, rtag)
            self.table.write(r, 1, tfile)
            r += 1
        self.table.set_current_row(r - 1)

    def choices(self, col: int):
        return self._choices

    def nrows(self):
        return len(self.data)

    def current_row(self) -> int:
        return self.table.current_row()

    def read(self, row: int, col: int) -> str:
        return self.data[row][col]

    def write(self, row: int, col: int, val: str):
        ## Update database, if value is valid
        # Check that the values are really new
        if col == 0:
            # Report-type field
            if not val:
                REPORT_ERROR(T("NO_REPORT_TYPE"))
                return
            for r in self.data:
                if r[0] == val:
                    REPORT_ERROR(T("TAG_NOT_NEW"))
                    return
            # Allow empty template: when adding a new entry, this field
            # must be filled before the template field.
            # It is also possible that a type is to be defined before a
            # template is available (?)
            self._update(self.data[row][2], val, self.data[row][1])
        elif val != self.data[row][1]:
            rt = self.data[row][0]
            if rt:
                self._update(self.data[row][2], rt, val)
            else:
                REPORT_ERROR(T("NO_REPORT_TYPE"))


class TableDelegate(QStyledItemDelegate):
    """Table delegate managing the report-type / template table.
    The handling of the underlying data is done by the object passed as
    <data_proxy>.
    """
    def __init__(self, table_widget, data_proxy):
        self._table = data_proxy
        super().__init__(parent = table_widget)
        ## Pop-up editors
        self._list_choice = ListChoice(table_widget)
        self._editor = QLineEdit()

    def write_cell(self, row: int, col: int, val: str):
        """Use this to manage setting table values. It allows the
        cell value to be displayed in a customized manner.
        """
        # There is no customization of the displayed values here
        self.parent().item(row, col).setText(val)

    def createEditor(self, parent, option, index):
        row, col = index.row(), index.column()
        tw = self.parent()  # NOT the same as <parent>!
        # The QTableWidget holds the "display" values, so to get the
        # underlying "actual" values, <self._table> is used.
        value = self._table.read(row, col)
        # or tw.item(row, col).text()
        #print("§createEditor:", row, col, value)
        if col == 0:
            # simple text
            e = self._editor
            e.setParent(parent)
            e.setText(value)
            return e
        else:
            # col == 1
            y = tw.rowViewportPosition(row)
            x = tw.columnViewportPosition(col)
            qp = parent.mapToGlobal(QPoint(x, y))
            self._list_choice.move(qp)
            v = self._list_choice.open(self._table.choices(col), value)
            if v is not None and v != value:
                #print("§saving:", value, "->", v)
                self._table.write(row, col, v)
            return None

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
        #print("§setModelData:", index.row(), index.column(), editor.text())
        self._table.write(index.row(), index.column(), editor.text())


def editGradeTableSelectionDialog(
    occasion: str = None,
    class_group: str = None,
    parent: Optional[QWidget] = None,
) -> Optional[tuple[str, str]]:     # return (occasion, class_group)

    print("§?0", occasion, class_group)

    class_group_list = []
    cgmap = {}

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = (occasion, class_group)

    @Slot(str)
    def on_occasion_list_currentTextChanged(text):
        nonlocal occasion, suppress_events
        print("§?4a", suppress_events, text, occasion)

        if suppress_events: return
        occasion = text
        suppress_events = True
        set_groups()
        suppress_events = False

    @Slot(str)
    def on_occasion_editor_textChanged(text):
        if text in occasions:
            ui.pb_new_occasion.setEnabled(False)
            ui.pb_edited_occasion.setEnabled(False)
            ui.pb_remove_occasion.setEnabled(True)
        else:
            ui.pb_new_occasion.setEnabled(bool(occasion))
            ui.pb_edited_occasion.setEnabled(bool(occasion))
            ui.pb_remove_occasion.setEnabled(False)

    @Slot(str)
    def on_group_list_currentTextChanged(text):
        nonlocal suppress_events
        if suppress_events: return
        suppress_events = True
        set_class_group(text)
        suppress_events = False

    @Slot(str)
    def on_combo_classes_currentTextChanged(c):
        if suppress_events: return
        class_group_changed(c, ui.group_editor.text())

    @Slot(str)
    def on_group_editor_textChanged(g):
        if suppress_events: return
        class_group_changed(ui.combo_classes.currentText(), g)

    @Slot()
    def on_pb_new_occasion_clicked():
        nonlocal occasion, suppress_events
        grc = db.table("GRADE_REPORT_CONFIG")
        o = ui.occasion_editor.text()
        if grc.add_records([{
            "OCCASION": o,
            "CLASS_GROUP": class_group,
            "REPORT_TYPE": "",
            "TEMPLATE": "",
        }]):
            # Reinitialize with <o> and <class_group>
            occasion = o
            init()

    @Slot()
    def on_pb_edited_occasion_clicked():
        nonlocal occasion, suppress_events
        # Check it is not in use
        if db.table("GRADES").grades_for_occasion_group(
            occasion, class_group
        ):
            REPORT_ERROR(T("GRADES_EXIST_FOR_OCCASION", o = occasion))
            return
        o = ui.occasion_editor.text()
        grc = db.table("GRADE_REPORT_CONFIG")
        for rtl in report_types[occasion].values():
            for _, _, id in rtl:
                grc.update_cell(id, "OCCASION", o)
        grc.reset()
        occasion = o
        init()

    @Slot()
    def on_pb_remove_occasion_clicked():
        nonlocal suppress_events
        # Check it is not in use
        if db.table("GRADES").grades_for_occasion_group(
            occasion, class_group
        ):
            REPORT_ERROR(T("GRADES_EXIST_FOR_OCCASION", o = occasion))
            return
        if not SHOW_CONFIRM(T("REALLY_DELETE_OCCASION", o = occasion)):
            return
        rowids = []
        for rtl in report_types[occasion].values():
            for _, _, id in rtl:
                rowids.append(id)
        grc = db.table("GRADE_REPORT_CONFIG")
        grc.delete_records(rowids)
        init()

    @Slot()
    def on_pb_new_group_clicked():
        nonlocal class_group, suppress_events
        grc = db.table("GRADE_REPORT_CONFIG")
        if grc.add_records([{
            "OCCASION": occasion,
            "CLASS_GROUP": new_class_group,
            "REPORT_TYPE": "",
            "TEMPLATE": "",
        }]):
            # Reinitialize with <occasion> and <new_class_group>
            class_group = new_class_group
            init()

    @Slot()
    def on_pb_remove_group_clicked():
        nonlocal suppress_events
        # Check it is not in use
        if db.table("GRADES").grades_for_occasion_group(
            occasion, class_group
        ):
            REPORT_ERROR(T("GRADES_EXIST_FOR_GROUP",
                o = occasion, cg = class_group
            ))
            return
        if not SHOW_CONFIRM(T("REALLY_DELETE_GROUP",
            o = occasion, cg = class_group
        )):
            return
        rowids = [id for _, _, id in report_types[occasion][class_group]]
        #print("???", rowids, report_types[occasion][class_group])
        grc = db.table("GRADE_REPORT_CONFIG")
        grc.delete_records(rowids)
        init()

    @Slot()
    def on_pb_remove_report_clicked():
        nonlocal suppress_events
        row = report_table.current_row()
        rowid = report_table.read(row, 2)
        rtype = report_table.read(row, 0)
        if rowid > 0 and rtype:
            # Check it is not in use
            for st, gm in db.table("GRADES").grades_for_occasion_group(
                occasion, class_group
            ).items():
                if gm.grades.get("REPORT_TYPE") == rtype:
                    REPORT_ERROR(T("REPORT_TYPE_IN_USE"))
                    return
            if not SHOW_CONFIRM(T("REALLY_DELETE_REPORT_TYPE",
                t = rtype, o = occasion, cg = class_group
            )):
                return
            grc = db.table("GRADE_REPORT_CONFIG")
            if report_table.nrows() == 1:
                # Keep entry, but clear tag and template
                grc.update_cells(TAG = "", TEMPLATE = "")
            else:
                grc.delete_records([rowid])
            init()
        #else: There is no database entry

    ##### functions #####

    def set_groups():
        ui.group_list.clear()
        cgmap.clear()
        cgmap.update(report_types.get(occasion))
        class_group_list[:] = sorted(cgmap, reverse = True)
        if cgmap:
            ui.group_list.addItems(class_group_list)
        try:
            i = class_group_list.index(class_group)
        except ValueError:
            i = 0
        ui.group_list.setCurrentRow(i)
        r = ui.group_list.currentRow()
        set_class_group(class_group_list[r])

    def set_class_group(cg):
        nonlocal class_group
        class_group = cg
        rlist = sorted(cgmap[cg])
        #print("\n§set_class_group:", cg, rlist)
        c, g = class_group_split(cg, whole_class = "")
        #print(f"§class + group: '{c}', '{g}'")
        ui.combo_classes.setCurrentText(c)
        ui.group_editor.setText(g)
        report_table.setup(rlist)
        #ui.pb_remove_report.setEnabled(bool(rlist))
        class_group_changed(c, g)

    def class_group_changed(c, g):
        nonlocal new_class_group
        new_class_group = format_class_group(c, g, whole_class = "")
        if new_class_group in cgmap:
            ui.pb_new_group.setEnabled(False)
            ui.pb_remove_group.setEnabled(True)
        else:
            ui.pb_new_group.setEnabled(True)
            ui.pb_remove_group.setEnabled(False)

    def init():
        nonlocal occasion, suppress_events
        suppress_events = True
        print("§?1")
        report_types.clear()
        report_types.update(db.table("GRADE_REPORT_CONFIG")._template_info)
        occasions[:] = sorted(report_types)
        print("§?1a", suppress_events)
        ui.occasion_list.clear()
        print("§?1b")
        ui.occasion_list.addItems(occasions)
        try:
            i = occasions.index(occasion)
        except ValueError:
            i = 0
            try:
                occasion = occasions[0]
            except IndexError:
#TODO: Is this case covered??
                occasion = ""
        ui.occasion_list.setCurrentRow(i)
        print("§?2")
        set_groups()
        suppress_events = False

    def update_report_type(rowid: int, report_type: str, template: str):
        """Manage updates to the report-type table
        """
        grc = db.table("GRADE_REPORT_CONFIG")
        if rowid:
            if not grc.update_cells(
                rowid, REPORT_TYPE = report_type, TEMPLATE = template
            ):
                return
            grc.reset()
        else:
            if not grc.add_records([{
                "OCCASION": occasion,
                "CLASS_GROUP": class_group,
                "REPORT_TYPE": report_type,
                "TEMPLATE": template,
            }]):
                return
        # Call indirectly to avoid (here harmless) error message
        QTimer.singleShot(0, init)

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
#    ui = load_ui("dialog_edit_grade_table_selection.ui", None, locals())
    ui = get_ui_locals(
        "dialog_edit_grade_table_selection.ui",
        parent = parent,
        fnmap = locals()
    )

    # Data initialization
    suppress_events = True
#    if title:
#        ui.label.setText(title)
#    ui.textline.setText(start_value or default)

    db = get_database()
    # Populate the class combobox
    class_list = db.table("CLASSES").class_list()
    class_list.reverse()
    ui.combo_classes.clear()
    ui.combo_classes.addItems(c for _, c, _ in class_list)
    table_1 = Table(ui.report_table)
    report_table = ReportTable(table_1, update_report_type)
    # Configuration data
    report_types = {}
    occasions = []
    new_class_group = None
    init()
    result = None
    suppress_events = False
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    ui.resize(0, 0)
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":

    print("\n----->", editGradeTableSelectionDialog(
        occasion = "2. HalbjahrX",
        class_group = "11G",
        parent = None,
    ))
