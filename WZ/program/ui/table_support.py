"""
ui/table_support.py

Last updated:  2024-01-12

Extend the interface to a QTableWidget.


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

from core.base import REPORT_ERROR, REPORT_WARNING
from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    ### QtCore
    Qt,
    QObject,
    QEvent,
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
    """
    def __init__(self, table):
        super().__init__()
        table.installEventFilter(self)
        self.table = table

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
#TODO: assert?
        assert len(selranges) == 1

        selrange = selranges[0]
        rrows = []
        for r in range(selrange.topRow(), selrange.bottomRow() + 1):
            rcols = []
            c0 = selrange.leftColumn()
            c1 = selrange.rightColumn() + 1
            for c in range(c0, c1):
                item = tw.item(r, c)
                rcols.append(item.text() if item else "")
            rrows.append('\t'.join(rcols))
        text = '\n'.join(rrows)
        #print("   -->", repr(text))
        APP.clipboard().setText(text)

    def paste_to_cells(self, rows: list[list[str]]):
        tw = self.table
        selranges = tw.selectedRanges()
#TODO: assert?
        assert len(selranges) == 1

        selrange = selranges[0]
        if pasteFit(rows, selrange.rowCount(), selrange.columnCount()):
            pass
            #print("NEW TABLE:", rows)
        else:
            REPORT_ERROR(T("BAD_PASTE_RANGE",
                rows = len(rows), cols = len(rows[0])
            ))
            return
        r = selrange.topRow()
        for row in rows:
            c = selrange.leftColumn()
            for value in row:
                item = tw.item(r, c)
                if item:
                    item.setText(value)
                elif value:
                    item = QTableWidgetItem(value)
                    tw.setItem(r, c, item)
                    REPORT_WARNING(T("FORCED_NEW_ITEM",
                        value = value, row = r, col = c
                    ))
                c += 1
            r += 1
