"""
ui/modules/grades_manager.py

Last updated:  2024-01-01

An alternative HeaderView for QTableView – the headers are rotated by 90°.


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
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
#    basedir = os.path.dirname(appdir)
#    from core.base import setup
#    setup(os.path.join(basedir, 'TESTDATA'))

### +++++

from ui.ui_base import (
    ### QtWidgets:
    QHeaderView,
    QStyleOptionHeader,
    QStyle,
    ### QtCore:
    Qt,
    QSize,
)

### -----

class RotatedHeaderView(QHeaderView):
    """Rotate header items by 90°.
    """
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self._horiz_columns = set()
        #self.setDefaultAlignment(Qt.AlignLeft)
        #self._font = QtGui.QFont("helvetica", 15)
        #self._metrics = QtGui.QFontMetrics(self._font)
        self._metrics = self.fontMetrics()
        self._descent = self._metrics.descent()
        self._margin = 10

    def set_horiz_index(self, index, on = True):
        if on:
            self._horiz_columns.add(index)
        else:
            self._horiz_columns.discard(index)

    def get_style_options(self, painter, rect, index, text):
        opt = QStyleOptionHeader()
        self.initStyleOption(opt)
        state = QStyle.State_None
        if self.isEnabled():
            state |= QStyle.State_Enabled
        if self.window().isActiveWindow():
            state |= QStyle.State_Active

        if (
            self.isSortIndicatorShown()
            and self.sortIndicatorSection() == index
        ):
            opt.sortIndicator = (
                QStyleOptionHeader.SortDOwn
                if self.sortIndicatorOrder() == Qt.AscendingOrder
                else QStyleOptionHeader.SortUp
            )
        # setup the style options structure
        opt.rect = rect
        opt.section = index
        opt.state |= state
        opt.iconAlignment = Qt.AlignVCenter
        text = self.model().headerData(index, self.orientation())
        opt.text = text
        # the section position
        visual = self.visualIndex(index)
        assert visual != -1
        if (self.count() == 1):
            opt.position = QStyleOptionHeader.OnlyOneSection
        elif (visual == 0):
            opt.position = QStyleOptionHeader.Beginning
        elif (visual == self.count() - 1):
            opt.position = QStyleOptionHeader.End
        else:
            opt.position = QStyleOptionHeader.Middle
        return opt

    def paintSection(self, painter, rect, index):
        if index in self._horiz_columns:
            super().paintSection(painter, rect, index)
            return
        text = self._get_data(index)
        opt = self.get_style_options(painter, rect, index, text)
        # Draw frame
        opt.text = ""
        #oldBO = painter.brushOrigin()
        painter.save()
        self.style().drawControl(QStyle.CE_Header, opt, painter, self)
        painter.restore()
        #painter.setBrushOrigin(oldBO)
        # Draw text
        painter.save()
        w, h = rect.width(), rect.height()
        painter.translate(rect.x(), rect.y() + h)
        painter.rotate(-90)
        painter.drawText(self._margin, w//2 + self._descent, text)
        painter.restore()

    def sizeHint(self):
        """Determine a height based on the text width, because of the
        rotation.
        """
        hmax = 0
        for i in range(0, self.model().columnCount()):
#TODO: Is there a better solution for invalid data here?
            try:
                brect = self._metrics.boundingRect(self._get_data(i))
            except TypeError:
                return QSize(0, 0)
            if i in self._horiz_columns:
                h = brect.height()
            else:
                h = brect.width()
            if h > hmax:
                hmax = h
        return QSize(0, hmax + 2 * self._margin)

## Not used by resizeColumnsToContents?
    def sectionSizeHint(self, column):
        assert False, "TODO?"
        return self._metrics.height()

    def _get_data(self, index):
        data = self.model().headerData(index, self.orientation())
        print("???", index, repr(data))
        return data


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":

    from ui.ui_base import QTableWidget, run
    tw = QTableWidget()
    nrows = 10
    cols = ("Long Column 100", "Column 2", "Col 3", "Col 4a", "Column 5")
    tw.setColumnCount(len(cols))
    tw.setRowCount(nrows)

    headerView = RotatedHeaderView()
    tw.setHorizontalHeader(headerView)
    tw.setHorizontalHeaderLabels(cols)

    # This doesn't really work because it uses the text width of the
    # headers. To support rotated headers properly, a custon column-width
    # function would be needed.
    #tw.resizeColumnsToContents()

    headerView.setMinimumSectionSize(20)

    for i in range(len(cols)):
        tw.setColumnWidth(i, 40 if i > 0 else 150)
        print("§width:", i, tw.columnWidth(i))
        print("§section-size:", headerView.sectionSizeHint(i))

    headerView.set_horiz_index(0, True)

    tw.resize(600, 400)
    run(tw)
