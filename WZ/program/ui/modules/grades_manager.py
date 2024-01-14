"""
ui/modules/grades_manager.py

Last updated:  2024-01-14

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
    QHeaderView,
    QAbstractButton,
    QTableWidgetItem,
    QStyledItemDelegate,
    QLineEdit,
    QComboBox,
    QDialog,
    QVBoxLayout,
    QCalendarWidget,
    #QCompleter,
    ### QtGui:
    QColor,
    QBrush,
    QValidator,
    ### QtCore:
    QObject,
    Qt,
    QEvent,
    QTimer,
    QDate,
    Slot,
    ### other
    APP,
    SHOW_CONFIRM,
    SAVE_FILE,
)
from ui.rotated_table_header import RotatedHeaderView
from ui.table_support import CopyPasteEventFilter

from core.base import REPORT_INFO, REPORT_ERROR, REPORT_WARNING
from core.basic_data import get_database, CONFIG
from core.dates import print_date
from core.list_activities import report_data
from core.classes import class_group_split_with_id
from grades.grade_tables import (
    #subject_map,
    grade_scale,
    valid_grade_map,
)
from grades.grade_tables import grade_table_data
from grades.ods_template import BuildGradeTable

### -----

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
#+
class TableComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.activated.connect(self._activated)
        #print("§view:", self.view())
        self.escape_filter = EscapeKeyEventFilter(self.view(), self.esc)

    def esc(self):
        print("§esc")

    def _activated(self, i):
# Not called on ESC
        print("§activated:", i)

    def hidePopup(self):
        print("§hidePopup")
        super().hidePopup()

    def keyPressEvent(self, event):
        print("§key:", event.key())
        super().keyPressEvent(event)
        if event.key() == Qt.Key_Escape:
            #self.clearFocus()
            self._activated(None)


class GradeTableDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super().__init__(parent)
        self._columns = []
        self._column_data = []

    def set_columns(self, column_types: list[str]):
        self.column_types = column_types

    def displayText(self, key, locale):
#        try:
#            return print_date(key)
##TODO
#        except:
            return key

    def destroyEditor(self, editor,  index):
        print("§destroyEditor")
#TODO: temporary ... in the end I expect nothing should be destroyed
        if self._columns[index.column()] not in ("GRADE", "CHOICE"):
            super().destroyEditor(editor,  index)

    def createEditor(self, parent, option, index):
        col = index.column()
        ctype = self._columns[col]
        print("§index:", col)
        if ctype == "GRADE":
            self._grade_editor.setParent(parent)
            return self._grade_editor
        if ctype == "CHOICE":
            editor = self._column_data[col]
            editor.setParent(parent)

            self._primed = False

            return editor

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        col = index.column()
        ctype = self._columns[col]
        print("§sed-index:", col, ctype)
        self._primed = False
        if ctype == "CHOICE":
            currentText = index.data(Qt.EditRole)
            cbIndex = editor.findText(currentText);
            # if it is valid, adjust the combobox
            if cbIndex >= 0:
                editor.setCurrentIndex(cbIndex)
            editor.showPopup()
        self._primed = True

        super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        super().setModelData(editor, model, index)
        #model.setData(index, editor.currentText(), Qt.EditRole)

    def _max_width(self, string_list: list[str]) -> tuple[int, int]:
        """Return the display width of the widest item in the list
        and the width of a single "M".
        """
        fm = self.parent().fontMetrics()
        w = 0
        for s in string_list:
            _w = fm.boundingRect(s).width()
            if _w > w:
                w = _w
        return w, fm.horizontalAdvance("M")

    def set_grade_map(self, glist: list[str]):
        """Set up the information for editing grade cells.
        """
        w, m = self._max_width(glist)
        self._min_grade_width = w + m
        self._grade_editor = QLineEdit()
        self._grade_validator = ListValidator(glist)
        self._grade_editor.setValidator(self._grade_validator)

    def clear(self):
        """Call this when initializing a table for a new group.
        """
        self._columns.clear()
        self._column_data.clear()

    def _done(self, editor):
        print("§done", self._primed)
        if self._primed:
            # Ensure the edited cell regains focus
            editor.parent().setFocus(Qt.FocusReason.PopupFocusReason)
            # Finish editing
#            self.commitData.emit(editor)
#            self.closeEditor.emit(editor)

    def add_column(self, grade_field) -> int:
        """Return the minimum width for the new column
        """
        if grade_field is None:
            ctype = "GRADE"
            w = self._min_grade_width
            data = None

        else:
            ctype = grade_field.TYPE
            if ctype == "CHOICE":
                items = grade_field.DATA.split()
                w, m = self._max_width(items)
                w += m * 2
                data = TableComboBox()
                data.addItems(items)
                data.currentIndexChanged.connect(
                    lambda x: self._done(data)
                )
#TODO: leaving the value unchanged doesn't remove editor overlay,
# which can lead to errors because the editor is wrong:
#   QAbstractItemView::commitData called with an editor that does not belong to this view
#   QAbstractItemView::closeEditor called with an editor that does not belong to this view

# Using "activated" instead of currentIndexChanged also has this problem,
# which is perhaps a bit surprising ... NO, it's not that, some other change
# is doing that!

            elif ctype == "DEFAULT":
                data = None
                w = 50
            else:
#TODO:
                #REPORT_WARNING(f"TODO:: Unknown column type: '{ctype}'")
                print(f"§WARNING:: Unknown column type: '{ctype}'")
                ctype = "DEFAULT"
                data = None
                w = 50
        self._columns.append(ctype)
        self._column_data.append(data)
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


#deprecated ...
class ListDelegate(QStyledItemDelegate):
    def __init__(self, validation_list, table, parent = None):
        super().__init__(parent)
        fm = table.fontMetrics()
        w = 0
        for s in validation_list:
            _w = fm.boundingRect(s).width()
            if _w > w:
                w = _w
        self.min_width = w + fm.horizontalAdvance("M")
        self._validator = ListValidator(validation_list)
        #self._completer = QCompleter(validation_list)

    def createEditor(self, parent, option, index):
        w = QLineEdit(parent)
        w.setValidator(self._validator)
        #w.setCompleter(self._completer)
        return w


class ComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, validation_list, table, parent = None):
        super().__init__(parent)
        self._items = validation_list
        fm = table.fontMetrics()
        w = 0
        for s in validation_list:
            _w = fm.boundingRect(s).width()
            if _w > w:
                w = _w
        self.min_width = w + fm.horizontalAdvance("M") * 2

    def _done(self, editor, i):
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

    def createEditor(self, parent, option, index):
        # Create the combobox and populate it
        cb = QComboBox(parent)
        cb.addItems(self._items)
        return cb

    def setEditorData(self, editor, index):
        # get the index of the text in the combobox that matches the
        # current value of the item
        currentText = index.data(Qt.EditRole)
        cbIndex = editor.findText(currentText);
        # if it is valid, adjust the combobox
        if cbIndex >= 0:
           editor.setCurrentIndex(cbIndex)
        editor.currentIndexChanged.connect(
            lambda x: self._done(editor, x)
        )

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)


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
        if open:
            self.cal.setSelectedDate(
                QDate.fromString(text, Qt.DateFormat.ISODate)
            )
        self.exec()

    def text(self):
        return self.result


class DateDelegate(QStyledItemDelegate):
    """An "item delegate" for displaying and editing date fields.
    """
    def __init__(self, table, parent = None):
        super().__init__(parent)
        fm = table.fontMetrics()
        self.min_width = (
            fm.boundingRect(print_date("2024-12-30")).width()
            + fm.horizontalAdvance("M")
        )
        # Use a "dummy" line editor (because it seems to work, while
        # other approaches are a bit difficult to get working ...)
        self._editor = QLineEdit()
        self._editor.setReadOnly(True)

    def editorEvent(self, event, model, option, index):
        print("§editorEvent")
        self._model = model
        return super().editorEvent(event, model, option, index)

    def destroyEditor(self, editor,  index):
        print("§destroyEditor")
        #super().destroyEditor(editor,  index)

    def createEditor(self, parent, option, index):
        print("§createEditor")
        self._editor.setParent(parent)
        #w = QLineEdit(parent)
        #w.setReadOnly(True)
        self._primed = None
        self._text = None
        return self._editor

    def setEditorData(self, editor, index):
        # For some reason (!?), this gets called again after the new value
        # has been set, thus the used of <self._primed>.
        if self._primed is None:
            self._primed = index.data(Qt.ItemDataRole.EditRole)
            #editor.setText(currentText)
            print("§ACTIVATE")
            QTimer.singleShot(0, lambda: self.popup(editor))
        else:
            print("§REPEATED ACTIVATION")

    def popup(self, editor):
        cal = Calendar(editor)
        cal.open(self._primed)
        self._text = cal.text()
        print(f"Calendar {self._primed} -> {self._text}")
        # Ensure the edited cell regains focus
        editor.parent().setFocus(Qt.FocusReason.PopupFocusReason)
        # Finish editing
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

    def setModelData(self, editor, model, index):
        print("§setModelData", self._text)
        if self._text is not None:
            model.setData(index, self._text, Qt.ItemDataRole.EditRole)


class DateDelegate_0(QStyledItemDelegate):
    """An "item delegate" for displaying and editing date fields.
    """
    def __init__(self, table, parent = None):
        super().__init__(parent)
        fm = table.fontMetrics()
        self.min_width = (
            fm.boundingRect(print_date("2024-12-30")).width()
            + fm.horizontalAdvance("M")
        )

    def editorEvent(self, event, model, option, index):
        print("§editorEvent")
        self._model = model
        return super().editorEvent(event, model, option, index)

    def destroyEditor(self, editor,  index):
        print("§destroyEditor")
        super().destroyEditor(editor,  index)

    def createEditor(self, parent, option, index):
        print("§createEditor")
        w = QLineEdit(parent)
        w.setReadOnly(True)
        #d = Calendar(parent)
        #d.setModal(True)
        self._primed = None
        self._text = None
        return w

    def setEditorData(self, editor, index):
        # For some reason, this gets called again after the new value
        # has been set, thus the used of <self._primed>.
        if self._primed is None:
            self._primed = index.data(Qt.ItemDataRole.EditRole)
            #editor.setText(currentText)
            print("§ACTIVATE")
            QTimer.singleShot(0, lambda: self.popup(editor))
        else:
            print("§REPEATED ACTIVATION")

    def popup(self, editor):
        cal = Calendar(editor)
        cal.set_text(self._primed)
        self._text = cal.text()
        print("Calendar ->", self._text)
        editor.parent().setFocus(Qt.FocusReason.PopupFocusReason)
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

    def setModelData(self, editor, model, index):
        print("§setModelData", self._text)
        #val = editor.text()
        if self._text is not None:
            model.setData(index, self._text, Qt.ItemDataRole.EditRole)


###########################
# Maybe something based on:
    '''
    class MyLineEdit(QLineEdit):
        def showEvent(self, event):
            if self.myPopup:
                QTimer.singleShot(0, self.myPopup.exec)
            super().showEvent(event)

    class MyItemDelegate(QStyledItemDelegate):
        def createEditor(self, parent, option, index):
            popup = QDialog(parent)

            popup.setMinimumSize(500, 200)
            edit = MyLineEdit(parent)
            edit.myPopup = popup
            return edit
    '''
############################

    def displayText(self, key, locale):
        try:
            return print_date(key)
#TODO
        except:
            return key



class ManageGradesPage(QObject):
    def __init__(self, parent=None):
        super().__init__()
        self.ui = load_ui("grades.ui", parent, self)
        tw = self.ui.grade_table
        tw.setItemDelegate(GradeTableDelegate(parent = tw))
        self.event_filter = CopyPasteEventFilter(tw)

        nrows = 10
        cols = ("Long Column 100", "Column 2", "Col 3", "Col 4a", "Column 5",)
        cols += ("Column n",) * 20
        tw.setColumnCount(len(cols))
        tw.setRowCount(nrows)

        headerView = RotatedHeaderView()
        tw.setHorizontalHeader(headerView)
        tw.setHorizontalHeaderLabels(cols)


        #headerView.setDefaultSectionSize(30) # what does this do?
        headerView.setMinimumSectionSize(20)
#        headerView.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
#        headerView.setSectionResizeMode(
#            0, QHeaderView.ResizeMode.ResizeToContents
#        )
#        headerView.set_horiz_index(0, True)
#        pItem = tw.horizontalHeaderItem(0)
#        pItem.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
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
        for i in range(len(cols)):
            tw.setColumnWidth(i, 20 if i > 0 else 150)
        #    print("§width:", i, tw.columnWidth(i))
        #    print("§section-size:", headerView.sectionSizeHint(i))




    def enter(self):
#TODO: This comment is probably inaccurate! I certainly intend to permit
# some changes (grades, maybe configuration, ...)
        ## The database tables that are loaded here are expected not to
        ## change during the activity of this grade-editor object.
        # Set up lists of classes, teachers and subjects for the course
        # filter. These are lists of tuples:
        #    (db-primary-key, short form, full name)
        db = get_database()
        self.db = db
        self.report_info = report_data(GRADES = True)[0] # only for the classes

#        cal = Calendar()
#        cal.exec()
#        print("§DATE:", cal.result)

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
        self.occasion_tag = self.ui.occasion_extra.currentText()
#TODO: Remove or replace this when the occasion-tag handling is implemented:
        assert self.occasion_tag == ""
        if '$' in self.occasion:
            REPORT_ERROR("TODO: '$'-occasions not yet implemented")
            self.ui.grade_table.clear()
            return

        self.info, self.subject_list, self.student_list = grade_table_data(
            occasion = self.occasion,
            class_group = self.class_group,
            report_info = self.report_info,
            grades = self.db.table("GRADES").grades_occasion_group(
                self.occasion, self.class_group, self.occasion_tag
            ),
        )
        tw = self.ui.grade_table
        tw.clear()
        #tw.clearSelection()
        # Set validation using column delegates
        gscale = grade_scale(self.class_group)
        grade_map = valid_grade_map(gscale)
        delegate = tw.itemDelegate()
        delegate.clear()
        delegate.set_grade_map(list(grade_map))
        ### Collect the columns
        self.col_sid = []
        headers = []
        handlers = []
        ## First the "pre-grade" columns
        gfields = self.db.table("GRADE_FIELDS").records
        for gf_i, rec in enumerate(gfields):
            if rec.SORTING >= 0:
                break
            gl = rec.GROUPS
            if gl == '*' or self.class_group in gl.split():
                self.col_sid.append(rec.NAME)
                headers.append(rec.LOCAL)
                handlers.append(rec)
        ## Now the grade columns
        for sbj in self.subject_list:
            headers.append(sbj.NAME)
            self.col_sid.append(sbj.id)
            handlers.append(None)
        ## Now the remaining extra columns
        for i in range(gf_i, len(gfields)):
            rec = gfields[i]
            gl = rec.GROUPS
            if gl == '*' or self.class_group in gl.split():
                self.col_sid.append(rec.NAME)
                headers.append(rec.LOCAL)
                handlers.append(rec)
        ## Set the table size
        tw.setColumnCount(len(headers))
        nrows = len(self.student_list)
        tw.setRowCount(nrows)
        tw.setHorizontalHeaderLabels(headers)

#        print("))) Table size set:", nrows, len(headers))

#TODO: Can/should LEVEL be optional? I would also need to look at the
# grade_tables (?) module
        for i, h in enumerate(handlers):
            tw.setColumnWidth(i, delegate.add_column(h))
#            if h is None:
#                # A grade column
#                tw.setColumnWidth(i, delegate.min_width(i))
#            elif h.TYPE == "DATE":
#                tw.setItemDelegateForColumn(i, self.date_delegate)
#                tw.setColumnWidth(i, self.date_delegate.min_width)
#            elif h.TYPE == "CHOICE":
#                #xdel = ListDelegate(h.DATA.split(), tw)
#                xdel = ComboBoxDelegate(h.DATA.split(), tw)
#                self.xdelegates.append(xdel)
#                tw.setItemDelegateForColumn(i, xdel)
#                tw.setColumnWidth(i, xdel.min_width)
#            else:
##TODO: other fields ...
#                tw.setColumnWidth(i, delegate.min_width())

#        print("))) Add students")
#        self.suppress_handlers = False
#        return

        ### Add students
        vheaders = []
        for i, stdata in enumerate(self.student_list):
            #print("%stadata:", stdata)
            pname = stdata["NAME"]
            vheaders.append(pname)
            grades = stdata["GRADES"]
#            plevel = grades.get("LEVEL") or ""
            #item = QTableWidgetItem(pname)
            #item.setBackground(QColor("#FFFF80"))
            #tw.setItem(i, 0, item)
#            item = QTableWidgetItem(plevel)
#            item.setBackground(QColor("#FFFF80"))
#            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#            tw.setItem(i, 0, item)
            # Add grades, etc.
            for j, s_id in enumerate(self.col_sid):
                try:
                    int(s_id)
                except ValueError:
                    # A non-grade entry
                    try:
                        val = grades[s_id]
                    except KeyError:
                        #print("§s_id:", repr(s_id))
                        if s_id.startswith("DATE_"):
#TODO
                            val = "2024-01-12"
                        else:
                            val = "??"
                    item = QTableWidgetItem(val)
                    item.setBackground(QColor("#FFFFA0"))

#TODO: I would need configuration involving translations for those
# items not in the main translations file, colour, delegate for display and
# editing, cell width, ...
#
# One significant project would be a delegate for dates (display and edit).

                else:
                    g = grades[str(s_id)]
                    item = QTableWidgetItem(g or "?")
#TODO ...
#                item.setBackground(QColor("#FABBFF"))
#                if j & 1:
#                    item.setBackground(QColor("#FAFFBB"))
#                elif j & 2:
#                    item.setBackground(QBrush())

                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tw.setItem(i, j, item)


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

    @Slot(QTableWidgetItem)
    def on_grade_table_itemChanged(self, item):
        if self.suppress_handlers: return
        print("§CHANGED:", item.row(), item.column(), item.text())


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from ui.ui_base import run

    widget = ManageGradesPage()
    widget.enter()
    widget.ui.resize(1000, 550)
    run(widget.ui)







'''

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


class _ManageGrades(Page):
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

'''
