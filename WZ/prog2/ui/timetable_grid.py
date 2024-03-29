"""
ui/timetable_grid.py

Last updated:  2024-03-29

A grid widget for the timetable displays.


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

#TODO: Probably needs a lot of fixing ...
# Use canvas.py as base

if __name__ == "__main__":
    import sys, os
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

### +++++

#TODO ...
from ui.ui_base import (
    APP,
    # QtWidgets
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsLineItem,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QMenu,
    # QtCore
    Qt,
    # QtGui
    QIcon,
    QPainter,
    QTransform,
    QRectF,
)
from ui.canvas import (
    Canvas,
    CanvasRescaling,
    StyleCache,
    Chip,
    CHIP_MARGIN,

#?
    MM2PT,
    PT2MM,
    A4,
)

_DAYWIDTH = 140.0
_VHEADERWIDTH = 80.0
_HHEADERHEIGHT = 40.0
_GRIDLINEWIDTH = 1.0
_GRIDLINECOLOUR = 'b0b0b0'

# Fonts
#FONT_HEADER_SIZE = 14
FONT_CENTRE_SIZE = 18
#FONT_CORNER_SIZE = 11

#?
_MARGIN_LEFT = 30
_MARGIN_RIGHT = 30
_MARGIN_TOP = 50
_MARGIN_BOTTOM = 50
_HEADER = 40
_FOOTER = 25

_TIMEWIDTH = 82
_BOXWIDTH = 142
_BOXHEIGHT = 51
_LINEWIDTH = 2
_TITLEHEIGHT = 30
_TITLEWIDTH = 82

_SUBTEXTGAP = 10    # minimum horizontal space between tile "subtexts"

# Colours (rrggbb)
BORDER_COLOUR = 'b0b0b0'    # '12c6f8'
HEADER_COLOUR = 'f0f0f0'
MARGIN_LINE_COLOUR = '000000'
BREAK_COLOUR = '606060'     # '6060d0'
#CELL_HIGHLIGHT_COLOUR = 'a0a0ff'
SELECT_COLOUR = 'ff0000'

# Tile corner enum
TILE_TOP_LEFT = 0
TILE_TOP_RIGHT = 1
TILE_BOTTOM_RIGHT = 2
TILE_BOTTOM_LEFT = 3

SIZES = {}

### -----


class GridView(CanvasRescaling):
    def __init__(self, view: QGraphicsView, period_times, days):
        super().__init__(view)
        _scene = view.scene()
        # Determine the grid cells using the period times and days
        hlines = []
        x0 = 0
        for tag, t0, t1 in period_times:
            h0, m0 = (int(t) for t in t0.split(":"))
            h1, m1 = (int(t) for t in t1.split(":"))
            mm0 = h0 * 60 + m0
            mm1 = h1 * 60 + m1
            if not x0:
                x0 = mm0
            hlines.append((float(mm0 - x0), float(mm1 - x0)))
        #print("???", hlines)
        self.ylines = hlines
        dlines = []
        d = 0.0
        for tag in days:
            dlines.append(d)
            d += _DAYWIDTH
        dlines.append(d)
        #print("???", dlines)

        w0 = dlines[-1]
        h0 = hlines[-1][1]
        width = w0 + _VHEADERWIDTH
        height = h0 + _HHEADERHEIGHT
        weekbox = QGraphicsRectItem(
            -_VHEADERWIDTH, -_HHEADERHEIGHT, width, height
        )
        _scene.addItem(weekbox)
        weekbox.setPen(StyleCache.getPen(_GRIDLINEWIDTH))
        weekbox.setZValue(10)
        for x in dlines:
            line = QGraphicsLineItem(x, -_HHEADERHEIGHT, x, h0)
            if x:
                line.setPen(
                    StyleCache.getPen(_GRIDLINEWIDTH, _GRIDLINECOLOUR)
                )
            else:
                line.setPen(StyleCache.getPen(_GRIDLINEWIDTH))
            _scene.addItem(line)
            #line.setZValue(-5)
        self.xlines = dlines
        for y01 in hlines:
            for y in y01:
                line = QGraphicsLineItem(-_VHEADERWIDTH, y, w0, y)
                if y:
                    line.setPen(
                        StyleCache.getPen(_GRIDLINEWIDTH, _GRIDLINECOLOUR)
                    )
                else:
                    line.setPen(StyleCache.getPen(_GRIDLINEWIDTH))
                _scene.addItem(line)
                #line.setZValue(-5)

        dpfont = StyleCache.getFont(size = 12)
        for i, d in enumerate(days):
            x0 = dlines[i]
            text_item = QGraphicsSimpleTextItem(d)
            text_item.setFont(dpfont)
            _scene.addItem(text_item)
            text_rect = text_item.boundingRect()
            text_width = text_rect.width()
            text_height = text_rect.height()
            xpos = x0 + (_DAYWIDTH - text_width) / 2
            ypos = -(_HHEADERHEIGHT + text_height) / 2
            text_item.setPos(xpos, ypos)

        tfont = StyleCache.getFont(size = 7)
        for i, pt in enumerate(period_times):
            tag, t0, t1 = pt
            y0, y1 = hlines[i]
            # First the period tag
            text_item = QGraphicsSimpleTextItem(tag)
            text_item.setFont(dpfont)
            _scene.addItem(text_item)
            text_rect = text_item.boundingRect()
            text_width = text_rect.width()
            text_height = text_rect.height()
            xpos = -(_VHEADERWIDTH + text_width) / 2
            ypos = (y1 + y0 - text_height) / 2
            text_item.setPos(xpos, ypos)
            # Now the times
            text_item = QGraphicsSimpleTextItem(f"{t0} – {t1}")
            text_item.setFont(tfont)
            _scene.addItem(text_item)
            text_rect = text_item.boundingRect()
            text_width = text_rect.width()
            text_height = text_rect.height()
            xpos = -(_VHEADERWIDTH + text_width) / 2
            ypos = y1 - text_height - CHIP_MARGIN
            #print("$$$", y0, y1, text_height)
            text_item.setPos(xpos, ypos)


#TODO--
class GridPeriodsDays(QGraphicsScene):
#    font_header = StyleCache.getFont(fontSize = FONT_HEADER_SIZE)

    def __init__(self, days, periods, breaks):
        self.tiles = {}
        super().__init__()
        SIZES["BOXWIDTH"] = (
            SIZES["TABLEWIDTH"] - SIZES["TITLEWIDTH"]
        ) / len(days)
        SIZES["BOXHEIGHT"] = (
            SIZES["TABLEHEIGHT"] - SIZES["TITLEHEIGHT"]
        ) / len(periods)
        self.xslots = [0]    # x-coordinate of column left side
        self.yslots = [0]    # y-coordinate of row top side
        # Cell at top left-hand corner
        self.addItem(Cell(0, 0, SIZES["TITLEWIDTH"], SIZES["TITLEHEIGHT"], -1, -1))
        # Add column headers
        x = SIZES["TITLEWIDTH"]
        icol = 0
        for col_header in days:
            self.xslots.append(x)
            cell = Cell(x, 0, SIZES["BOXWIDTH"], SIZES["TITLEHEIGHT"], -1, icol)
            cell.set_text(col_header, self.font_header)
            cell.set_background(HEADER_COLOUR)
            self.addItem(cell)
            icol += 1
            x += SIZES["BOXWIDTH"]
        self.grid_width = x
        # Add row headers and rows
        self.cell_matrix = []
        irow = 0
        y = SIZES["TITLEHEIGHT"]
        for row_header in periods:
            if row_header in breaks:
                line = QGraphicsLineItem(0, y, self.grid_width, y)
                line.setPen(StyleCache.getPen(SIZES["LINEWIDTH"], BREAK_COLOUR))
                self.addItem(line)
                line.setZValue(1)
            day_list = []
            self.cell_matrix.append(day_list)
            self.yslots.append(y)
            # row header
            cell = Cell(0, y, SIZES["TITLEWIDTH"], SIZES["BOXHEIGHT"], irow, -1)
            cell.set_text(row_header, self.font_header)
            cell.set_background(HEADER_COLOUR)
            self.addItem(cell)
            # day cells
            for i in range(icol):
                cell = Cell(self.xslots[i + 1], y, SIZES["BOXWIDTH"], SIZES["BOXHEIGHT"], irow, i)
                day_list.append(cell)
                self.addItem(cell)
            irow += 1
            y += SIZES["BOXHEIGHT"]
        self.grid_height = y
        # Set colour of main border lines
        for y in 0, SIZES["TITLEHEIGHT"], self.grid_height:
            line = QGraphicsLineItem(0, y, self.grid_width, y)
            line.setPen(StyleCache.getPen(SIZES["LINEWIDTH"], MARGIN_LINE_COLOUR))
            self.addItem(line)
            line.setZValue(10)
        for x in *self.xslots, self.grid_width:
            line = QGraphicsLineItem(x, 0, x, self.grid_height)
            line.setPen(StyleCache.getPen(SIZES["LINEWIDTH"], MARGIN_LINE_COLOUR))
            self.addItem(line)
            line.setZValue(10)

# Not using the selection rectangle from grid_support?
        # Make a rectangle for the "selected" marking
        self.select = QGraphicsRectItem(0, 0, SIZES["BOXWIDTH"], SIZES["BOXHEIGHT"])
        self.select.setPen(StyleCache.getPen(SIZES["LINEWIDTH"]*2, SELECT_COLOUR))
        self.select.setZValue(20)
        self.select.hide()
        self.addItem(self.select)

        self.make_context_menu()

    def make_context_menu(self):
        self.context_menu = QMenu()
        Action = self.context_menu.addAction("I am context Action 1")
        Action.triggered.connect(self.context_1)

    def get_cell(self, row, col):
        return self.cell_matrix[row][col]

    def mousePressEvent(self, event):
        point = event.scenePos()
        items = self.items(point)
        if items:
            if event.button() == Qt.MouseButton.LeftButton:
#TODO ...
                kbdmods = APP.keyboardModifiers()
                shift = (
                    " + SHIFT"
                    if kbdmods & Qt.KeyboardModifier.ShiftModifier
                    else ""
                )
                alt = (
                    " + ALT"
                    if kbdmods & Qt.KeyboardModifier.AltModifier
                    else ""
                )
                ctrl = (
                    " + CTRL"
                    if kbdmods & Qt.KeyboardModifier.ControlModifier
                    else ""
                )
                cell = None
                tiles = []
                item0 = None
                for item in items:
                    try:
                        cell = item.cell
                        item0 = item
                    except AttributeError:
                        tiles.append(item)
                for tile in tiles:
                    # Give all tiles at this point a chance to react, starting
                    # with the topmost. An item can break the chain by
                    # returning a false value.
                    try:
                        if not tile.leftclick():
                            return
                    except AttributeError:
                        pass
                if cell:
                    print (f"Cell – left press{shift}{ctrl}{alt} @ {item.cell}")
# Note that ctrl-click is for context menu on OSX ...
                    if shift:
#???
                        self.place_tile("T2", cell)
                    if alt:
                        self.select_cell(cell)

    def contextMenuEvent(self, event):
        point = event.scenePos()
        items = self.items(point)
        if items:
            for item in items:
                try:
                    # See if the topmost item is a tile
                    self.context_tag = item.tag
                except AttributeError:
                    # Not a tile. Otherwise there should only be a cell,
                    # but give all items a chance to react. An item can
                    # break the chain by returning a false value.
                    try:
                        fn = item.contextmenu
                    except AttributeError:
                        continue
                    if not fn(event.screenPos()):
                        return
                else:
                    self.context_menu.exec(event.screenPos())
#                    self.tile_context_menu(event.screenPos())
                    return

    def context_1(self):
        print(self.context_tag)

    def new_tile(self, tag, duration, nmsg, offset, total, text, colour=None):
        t = Tile(tag, duration, nmsg, offset, total, text, colour)
        self.addItem(t)
        self.tiles[tag] = t
        return t

    def remove_tiles(self):
        for tag, tile in self.tiles.items():
            self.removeItem(tile)
        self.tiles.clear()

    def place_tile(self, tag, cell):
        tile = self.tiles[tag]
        col, row = cell
        x = self.xslots[col + 1]    # first cell is header
        y = self.yslots[row + 1]    # first cell is header
        tile.set_cell(x, y)
#TODO: It might be useful for a tile to know where it is placed.
#        tile.cell = cell

    def select_cell(self, cell):
        x = self.xslots[cell[0] + 1]    # first cell is header
        y = self.yslots[cell[1] + 1]    # first cell is header
        self.select.setPos(x, y)
        self.select.show()


#TODO
class Tile(Chip):
    __slots__ = (
        "duration",
    )

    def __init__(
        self,
        canvas: Canvas,
        tag: str,               # tile tag (id)
        duration: int,          # number of periods
        groups: list[str],      # group tags
        div_groups: list[str],  # all group tags in division
        text: str,              # central text
        colour: str = None,     # "RRGGBB" (<None> => white)
    ):
        self.duration = duration
        super().__init__(
            canvas, tag, width = 100.0, height = 100.0,
            hover = None,
        )
#TODO

        self.set_background(colour)
        self.set_text(text, size = FONT_CENTRE_SIZE)
        #self.setZValue(5)
#?
        self.hide()


#TODO
    def set_cell(self, x, y):
        self.setPos(x, y)
        self.show()

    def set_corner(self, corner, text):
        """Place a text item in one of the four corners.
        """
        text_item = self.corners[corner]
        if not text_item:
            text_item = QGraphicsSimpleTextItem(self)
            text_item.setFont(self.font_corner)
            self.corners[corner] = text_item
        text_item.setText(text)
        if corner == TILE_TOP_LEFT:
            self.fit_corners(text_item, self.corners[TILE_TOP_RIGHT], True)
        elif corner == TILE_TOP_RIGHT:
            self.fit_corners(self.corners[TILE_TOP_LEFT], text_item, True)
        elif corner == TILE_BOTTOM_RIGHT:
            self.fit_corners(self.corners[TILE_BOTTOM_LEFT], text_item, False)
        elif corner == TILE_BOTTOM_LEFT:
            self.fit_corners(text_item, self.corners[TILE_BOTTOM_RIGHT], False)
        else:
            raise Bug(f"Invalid Tile Corner: {corner}")

#TODO: I might need some sort of line wrapping if the text is very long ...
    def fit_corners(self, left, right, is_top):
        width = self.width - SIZES["LINEWIDTH"] - SIZES["SUBTEXTGAP"]
        if left:
            br = left.boundingRect()
            left_width = br.width()
            left_height = br.height()
        else:
            left_width = 0
            left_height = 0
        if right:
            br = right.boundingRect()
            right_width = br.width()
            right_height = br.height()
        else:
            right_width = 0
            right_height = 0
        part = (left_width + right_width) / width
        scale = 1 / part if part > 1 else 1
        if left:
            left.setScale(scale)
            left_width *= scale
            if is_top:
                left.setPos(self.x + SIZES["LINEWIDTH"], SIZES["LINEWIDTH"])
            else:
                left.setPos(
                    self.x + SIZES["LINEWIDTH"],
                    self.height - SIZES["LINEWIDTH"] - left_height
                )
        if right:
            right.setScale(scale)
            right_width *= scale
            if is_top:
                right.setPos(
                    self.x + self.width - SIZES["LINEWIDTH"] - right_width,
                    SIZES["LINEWIDTH"]
                )
            else:
                right.setPos(
                    self.x + self.width - SIZES["LINEWIDTH"] - right_width,
                    self.height - SIZES["LINEWIDTH"] - right_height
                )

#TODO: May be useful (to get screen coordinates)?
#def get_pos(view, item, point):
#        scenePos = item.mapToScene(point)
#        viewportPos = view.mapFromScene(scenePos)
#        viewPos = view.viewport().mapToParent(viewportPos)
#        globalViewPos = view.mapToGlobal(QPoint(0, 0))
#        return globalViewPos.x + viewPos.x, globalViewPos.y + viewPos.y

#TODO
#    def printName(self):
#        print("Action triggered from {}".format(self.tag))


class Box(QGraphicsRectItem):
    """A rectangle with adjustable borderwidth.
    The item's coordinate system starts at (0, 0), fixed by passing
    this origin to the <QGraphicsRectItem> constructor.
    The box is then moved to the desired location using <setPos>.
    """
    __slots__ = (
        "text_item",
    )
    def __init__(self, x, y, w, h, width=None, colour=None):
        super().__init__(0, 0, w, h)
        self.setPos(x, y)
        self.setPen(StyleCache.getPen(width, colour or BORDER_COLOUR))
#
    def set_text(self, text, font=None):
        """Set a centred text item. Calling the function a second time
        updates the text.
        """
        try:
            item = self.text_item
        except AttributeError:
            item = QGraphicsSimpleTextItem(self)
            self.text_item = item
        if font:
            item.setFont(font)
        item.setText(text)
        bdrect = item.boundingRect()
        #print("§§§", text, bdrect)
        wt = bdrect.width()
        ht = bdrect.height()
        rect = self.rect()
        xshift = (rect.width() - wt) / 2
        yshift = (rect.height() - ht) / 2
        item.setPos(xshift, yshift)

    def set_background(self, colour):
        """Set the cell background colour.
        <colour> can be <None> ("no fill") or a colour in the form 'RRGGBB'.
        """
        self.setBrush(StyleCache.getBrush(colour))

###

class Cell(Box):
    """This is a rectangle representing a single period slot. It is used
    to construct the basic timetable grid.
    It is a <Box> whose background colour is settable and which supports
    hover events.
    """
    __slots__ = (
        "x0",
        "y0",
        "cell",
    )
#TODO: highlighting by emphasizing the border:
#    selected = None

#    @classmethod
#    def setup(cls):
#        cls.nBrush = StyleCache.getBrush(None)
#        cls.hBrush = StyleCache.getBrush(CELL_HIGHLIGHT_COLOUR)
#        cls.nPen = StyleCache.getPen(SIZES["SIZES["LINEWIDTH"]"] + 2, BORDER_COLOUR)
#        cls.sPen = StyleCache.getPen(SIZES["SIZES["LINEWIDTH"]"] + 2, SELECT_COLOUR)

#    @classmethod
#    def select(cls, cell):
#        if cls.selected:
#            cls.selected.setPen(cls.nPen)
#            cls.selected.setZValue(0)
#            cls.selected = None
#        if cell:
#            cell.setPen(cls.sPen)
#            cell.setZValue(20)
#            cls.selected = cell

    def __init__(self, x, y, w, h, irow, icol):
        """Create a box at scene coordinates (x, y) with width w and
        height h. irow and icol are row and column indexes.
        """
        super().__init__(x, y, w, h, width=SIZES["LINEWIDTH"])
        self.x0 = x
        self.y0 = y
        self.cell = (icol, irow)
#        self.setAcceptHoverEvents(True)
#        print ("Cell", icol, irow, x, y)

#TODO
    def contextmenu(self, event):
        print(f"CONTEXT MENU @ (col: {self.cell[0]} | row: {self.cell[1]})")
        return True # propagate down (though a <Cell> should be the lowest ...)

#TODO: It may be more appropriate to have the hover events handled in
# <Tile>.
#    def hoverEnterEvent(self, event):
#        print("Enter", self.cell)

#    def hoverLeaveEvent(self, event):
#        print("Leave", self.cell)


#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

def main(args):
#TODO: Will need various font sizes ...
# And playing around with the app font may not be such a good idea!
#    font = APP.font()
    #print("FONT:", font.pointSize())
#    font.setPointSize(12)
#    APP.setFont(font)

    #from qtpy.QtGui import QFontInfo
    #qfi = QFontInfo(font)
    #print("FONT PIXELS / POINTS:", qfi.pixelSize(), qfi.pointSize())
    WINDOW = GridViewRescaling()
    #WINDOW = GridViewHFit()
    #WINDOW = GridView()

    # Set up grid
    grid = GridPeriodsDays(DAYS, PERIODS, BREAKS)
    WINDOW.setScene(grid)

#### Actually, I'm not sure what sort of scaling makes sense ...
#### Probably best to use GridViewRescaling
#    # Scaling: only makes sense if using basic, unscaled GridView
#    scale = WINDOW.pdpi / WINDOW.ldpi
#    print("§SCALING", WINDOW.pdpi, WINDOW.ldpi, scale)
#    t = QTransform().scale(scale, scale)
##    WINDOW.setTransform(t)

#TODO: Only standalone!
    APP.setWindowIcon(QIcon(APPDATAPATH("icons/tt.svg")))
    screen = APP.primaryScreen()
    screensize = screen.availableSize()
    print("§screensize =", screensize)
    WINDOW.resize(int(screensize.width()*0.6), int(screensize.height()*0.75))
    WINDOW.show()

    return WINDOW


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    PERIOD_TIMES = [
        ("A", "08:10", "09:00"),
        ("B", "09:05", "09:50"),
        ("1", "10:10", "10:55"),
        ("2", "11:00", "11:45"),
        ("3", "12:00", "12:45"),
        ("4", "12:50", "13:35"),
        ("5", "13:45", "14:30"),
        ("6", "14:30", "15:15"),
        ("7", "15:15", "16:00"),
    ]
    DAYS = ["Mo", "Di", "Mi", "Do", "Fr"]

    window = GridView(QGraphicsView(), PERIOD_TIMES, DAYS)


    _scene = window.view.scene()
    scene_rect = _scene.sceneRect()
    frame = QGraphicsRectItem(scene_rect.adjusted(-5.0, -5.0, 5.0, 5.0))
    frame.setPen(StyleCache.getPen(0))
    _scene.addItem(frame)
#    A4rect = QRectF(0.0, 0.0, A4[0], A4[1])
#    _scene.addItem(QGraphicsRectItem(A4rect))
    scene = window.scene



    screen = APP.primaryScreen()
    screensize = screen.availableSize()
    print("§screensize =", screensize)
    window.view.resize(
        int(screensize.width()*0.6),
        int(screensize.height()*0.75)
    )
    window.view.show()

    sys.exit(APP.exec())
