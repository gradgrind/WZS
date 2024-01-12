import sys, os
this = sys.path[0]
appdir = os.path.dirname(this)
sys.path[0] = appdir
#basedir = os.path.dirname(appdir)

from ui.ui_base import (
    QStyledItemDelegate, QTableWidget, QTableWidgetItem, run, QComboBox,
    Qt,
    QLineEdit, QCompleter, QTimer, QDialog,
    QAbstractItemView,
    QColor,
    QHeaderView,
    QSize,
    QRect,

    QStyle,
    QStyleOptionHeader,
    QObject,
    QWidget,
    QEvent,
    APP,
)
from tables.table_utilities import TSV2Table, pasteFit, html2Table


class RotatedHeaderView(QHeaderView):
    """Rotate header items by 90°.
    """
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        #self.setDefaultAlignment(Qt.AlignLeft)
        #self._font = QtGui.QFont("helvetica", 15)
        #self._metrics = QtGui.QFontMetrics(self._font)
        self._metrics = self.fontMetrics()
        self._descent = self._metrics.descent()
        self._margin = 10

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

#        oldBO = painter.brushOrigin()
#        print("???1", painter.brushOrigin())

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

        opt.text = ""
        painter.save()
        self.style().drawControl(QStyle.CE_Header, opt, painter, self)
        painter.restore()
#        painter.setBrushOrigin(oldBO)
#        print("???2", painter.brushOrigin())
        return opt

    def paintSection(self, painter, rect, index):
        text = self._get_data(index)
        #print("§§§1", rect)
        opt = self.get_style_options(painter, rect, index, text)

        #print("§text:", text)

        painter.save()
        w, h = rect.width(), rect.height()
        painter.translate(rect.x(), rect.y() + h)
        painter.rotate(-90)
        painter.drawText(self._margin, w//2 + self._descent, text)
        painter.restore()

    def sizeHint(self):
        """Determine a height based on the text width.
        """
        return QSize(0, self._get_text_width() + 2 * self._margin)

## Not used by resizeColumnsToContents?
    def sectionSizeHint(self, column):
        return self._metrics.height()

    def _get_text_width(self):
        return max([self._metrics.boundingRect(self._get_data(i)).width()
                    for i in range(0, self.model().columnCount())])

    def _get_data(self, index):
        return self.model().headerData(index, self.orientation())

#You can use this class in your view as follows:
# headerView = MyHeaderView()
# tableView.setHorizontalHeader(headerView)


class ReadOnlyDelegate(QStyledItemDelegate):
    def createEditor(self, *args):
        return None


class ComboBoxItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        # Create the combobox and populate it
        cb = QComboBox(parent)
        row = index.row()
        cb.addItem(f"one in row {row}")
        cb.addItem(f"two in row {row}")
        cb.addItem(f"three in row {row}")
        return cb

    def setEditorData(self, editor, index):
        # get the index of the text in the combobox that matches the
        # current value of the item
        currentText = index.data(Qt.EditRole)
        cbIndex = editor.findText(currentText);
        # if it is valid, adjust the combobox
        if cbIndex >= 0:
           editor.setCurrentIndex(cbIndex)

#    def setModelData(self, editor, model, index):
#        model.setData(index, editor.currentText(), Qt.EditRole)


class LineEdit(QLineEdit):
    def showEvent(self, event):
        if self.completer() is not None:
            QTimer.singleShot(0, self.completer().complete)
        super().showEvent(event)


class CompleterItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        completer = QCompleter(["test", "test2", "alternative", "other", "taste"])
        completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        edit = LineEdit(parent)
        edit.setCompleter(completer)
        return edit

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


class EventFilter(QObject):
    """Implement an event filter for key presses on the table.
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
# Rather with selection ranges?
        selranges = tw.selectedRanges()
        assert len(selranges) == 1
        selrange = selranges[0]
        print("§selrange:", selrange)
        print("§ranges:",
            selrange.topRow(),
            selrange.leftColumn(),
            selrange.bottomRow(),
            selrange.rightColumn(),
        )

        '''
        copied_cells = sorted(tw.selectedIndexes())
        assert copied_cells
        #print("???", copied_cells)
        copy_rows = []
        copy_items = []
        max_column = copied_cells[-1].column()
        max_row = copied_cells[-1].row()
        '''

        rrows = []
        for r in range(selrange.topRow(), selrange.bottomRow() + 1):
            rcols = []
            for c in range(selrange.leftColumn(), selrange.rightColumn() + 1):
                item = tw.item(r, c)
                rcols.append(item.text() if item else "")
            rrows.append('\t'.join(rcols))
        text = '\n'.join(rrows)


        '''
        for c in copied_cells:
            #print("§§§", c.column(), max_column, copy_items)
            item = tw.item(c.row(), c.column())
            copy_items.append(item.text() if item else "")
            if c.column() == max_column:
                copy_rows.append('\t'.join(copy_items))
                copy_items = []
        text = '\n'.join(copy_rows)
        '''
        #print("   -->", repr(text))
        APP.clipboard().setText(text)

    def paste_to_cells(self, rows: list[list[str]]):
        tw = self.table


# Rather with selection ranges?
        selranges = tw.selectedRanges()
        assert len(selranges) == 1
        selrange = selranges[0]
        print("§selrange:", selrange)
        print("§ranges:",
            selrange.topRow(),
            selrange.leftColumn(),
            selrange.bottomRow(),
            selrange.rightColumn(),
        )


        if pasteFit(rows, selrange.rowCount(), selrange.columnCount()):
            print("NEW TABLE:", rows)
        else:
            h = len(rows)
            w = len(rows[0])
#TODO
            #REPORT_ERROR(f"Bad paste range, clipboard dimensions: {h} x {w}")
            print(f"!!! Bad paste range, clipboard dimensions: {h} x {w}")
            return

        '''
        selection = tw.selectedIndexes()
        if selection:
            row_anchor = selection[0].row()
            column_anchor = selection[0].column()
            for indx_row, row in enumerate(rows):
                for indx_col, value in enumerate(row):
                    r = row_anchor + indx_row
                    c = column_anchor + indx_col
                    if r < tw.rowCount() and c < tw.columnCount():
                        tw.item(r, c).setText(value)
        '''

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
#TODO
                    #REPORT_WARNING
                    print(
                        f"!!! A value ({value}) was set at ({r}, {c}),"
                        " but the cell was not previously initialized,"
                        " so the formatting could be wrong."
                    )
                c += 1
            r += 1


####### A styled tableview with delete-cell and activate-on-return handling

#class XTableView(QTableView):
#    def keyPressEvent(self, e):
#        key = e.key()
#        i = self.currentIndex()
#        if not self.isPersistentEditorOpen(i):
#            if key == Qt.Key_Return:
#                # start editing
#                self.edit(i)
#                return
#            elif key == Qt.Key_Delete:
#                # clear cell
#                self.model().setData(i, "")
#                return
#        super().keyPressEvent(e)

#    table = XTableView()
#    table.setStyleSheet(
#        """QTableView {
#           selection-background-color: #e0e0ff;
#           selection-color: black;
#        }
#        QTableView::item:focus {
#            selection-background-color: #d0ffff;
#        }
#        """
#    )


class TableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
#        self.activated.connect(self.do_activated)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked # this one has a delay!
        )
# Note that the <Return> key doesn't cause the editor to be opened ...
# Event handling may be necessary for that ... but see below!

    def do_activated(self):
        i = self.currentItem()
        print("Activated", self.currentRow(), self.currentColumn())
        # Note that there must be a TableWidgetItem installed on the
        # cell for this to work!
        if self.state() != self.EditingState:
            self.editItem(self.currentItem())

    def keyPressEvent(self, e):
        key = e.key()
        if key == Qt.Key_Return and self.state() != self.EditingState:
            self.editItem(self.currentItem())
        else:
            super().keyPressEvent(e)


tw = TableWidget()
headerView = RotatedHeaderView()

cbid = ComboBoxItemDelegate(tw)
cpid = CompleterItemDelegate(tw)
myid = MyItemDelegate(tw)
roid = ReadOnlyDelegate(tw)
# ComboBox only in column 2
tw.setItemDelegateForColumn(1, cbid)
# Completer only in column 3
tw.setItemDelegateForColumn(2, cpid)
# My delegate only in column 4
tw.setItemDelegateForColumn(3, myid)
# Column 5 is read-only
tw.setItemDelegateForColumn(4, roid)
ncols, nrows = 5, 10
tw.setColumnCount(ncols)
tw.setRowCount(nrows)

tw.setHorizontalHeader(headerView)
tw.setHorizontalHeaderLabels(("Column 100", "Column 2", "Col 3", "Column 4", "Column 5"))

for i in range(ncols):
    tw.setColumnWidth(i, 10)

colours = [
    QColor(255, 200, 230),
    QColor("#EEFFDD"),
    QColor("#ffddee"),
    QColor("#ddeeff"),
    QColor("#eeddff"),
]
for r in range(nrows):
    if r & 2:
        for c in range(ncols):
            twi = QTableWidgetItem()
            twi.setText(f"({r} | {c})")
#???
            twi.setBackground(colours[c])
            tw.setItem(r, c, twi)

#tw.resizeColumnsToContents() # doesn't work – uses header text width?
# Might need to get width of each cell in column (measure text)

print("???headerView._descent:", headerView._descent)
for c in range(ncols):
    print("COL", c, headerView.sectionSizeHint(c))

event_filter = EventFilter(tw)

tw.resize(600,400)
run(tw)
