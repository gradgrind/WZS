"""
ui/course_table.py

Last updated:  2023-11-30

Extend the interface to a QTableWidget.


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

from ui.ui_base import (
    ### QtWidgets:
    QTableWidget,
    QTableWidgetItem,
    ### QtCore
    Qt,
)

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
