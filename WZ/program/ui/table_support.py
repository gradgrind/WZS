"""
ui/table_support.py

Last updated:  2024-02-11

Support for table widgets, extending their capabilities.


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

from core.base import Tr
T = Tr("tables.table_support")

from core.base import REPORT_ERROR, REPORT_CRITICAL
from ui.ui_base import (
    ### QtWidgets:
    QDialog,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QCalendarWidget,
    QVBoxLayout,
    QListWidget,
    QTextEdit,
    QDialogButtonBox,
    QStyle,
    ### QtCore
    Qt,
    QObject,
    QEvent,
    QPoint,
    QDate,
    QTimer,
    APP,
)
from tables.table_utilities import TSV2Table, pasteFit, html2Table


class Table:
    """A wrapper around a QTableWidget to encapsulate the interface
    needed in, for example, the course editor.
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


class CopyPasteEventFilter(QObject):
    """Implement an event filter for a table widget to allow copy and paste
    operations on a table, triggered by Ctrl-C and Ctrl-V.
    Writing is done by means of a <write> method on the table, reading by
    means of a <read> method. The read method should have an extra
    argument to indicate whether the underlying (actual) value or the
    displayed value is read. Normally it will be the underlying value.
    """
    def __init__(self, table, copy_internal = True):
        """The parameter <copy_internal> determines whether the underlying
        value of a cell is copied rather than its displayed value. It is
        true by default, but this is only significant if the displayed value
        differs from the stored value.
        """
        super().__init__()
        table.installEventFilter(self)
        self.table = table
        self.copy_internal = copy_internal

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if (
                key == Qt.Key.Key_C
                and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            ):
                self.copy_selected_cells()
                return True
            elif (
                key == Qt.Key.Key_V
                and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            ):
                clip = APP.clipboard()
                mime_data = clip.mimeData()
                if mime_data.hasHtml():
                    html = mime_data.html()
                    tt = html2Table(html)
                    #print("Ctl-V (html):", tt)
                    if tt:
                        self.paste_to_cells(tt)
                elif mime_data.hasText():
                    tt = TSV2Table(mime_data.text())
                    #print("Ctl-V (text):", tt)
                    if tt:
                        self.paste_to_cells(tt)
                return True
        # otherwise standard event processing
        return False

    def copy_selected_cells(self):
        tw = self.table
        selranges = tw.selectedRanges()
        if len(selranges) != 1:
            REPORT_CRITICAL("Bug: multiple selection ranges")
        selrange = selranges[0]
        rrows = []
        for r in range(selrange.topRow(), selrange.bottomRow() + 1):
            rcols = []
            c0 = selrange.leftColumn()
            c1 = selrange.rightColumn() + 1
            for c in range(c0, c1):
                rcols.append(tw.read(r, c, self.copy_internal))
            rrows.append('\t'.join(rcols))
        text = '\n'.join(rrows)
        #print("   -->", repr(text))
        APP.clipboard().setText(text)

    def paste_to_cells(self, rows: list[list[str]]):
        tw = self.table
        selranges = tw.selectedRanges()
        if len(selranges) != 1:
            REPORT_CRITICAL("Bug: multiple selection ranges")
        selrange = selranges[0]
        # <pasteFit> might modify the dimensions of the input data!
        if not pasteFit(rows, selrange.rowCount(), selrange.columnCount()):
            REPORT_ERROR(T("BAD_PASTE_RANGE",
                rows = len(rows), cols = len(rows[0])
            ))
            return
        r = selrange.topRow()
        c0 = selrange.leftColumn()
        for row in rows:
            c = c0
            for value in row:
                tw.write(r, c, value)
                c += 1
            r += 1


###### Pop-up cell editors ######

class Calendar(QDialog):
    def __init__(self, parent = None):
        super().__init__(parent = parent)
        self.setWindowFlags(Qt.WindowType.SplashScreen)
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
#        p = self.parent()
#        if p:
#            self.move(p.mapToGlobal(QPoint(0, 0)))
        self.exec()
        return self.result

    def done_ok(self, item):
        self.result = item.text()
        self.accept()


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
#        p = self.parent()
#        if p:
#            self.move(p.mapToGlobal(QPoint(0, 0)))
        self.exec()
        return self.result

    def changed(self):
        if self.suppress_handlers: return
        self.current = self.te.toPlainText()
        self.bb.button(QDialogButtonBox.StandardButton.Ok).setDisabled(
            self.current == self.text0
        )


