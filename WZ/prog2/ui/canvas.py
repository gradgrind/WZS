"""
ui/canvas.py

Last updated:  2024-03-28

Provide some basic canvas support using the QGraphics framework.


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
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

### +++++

import re

#TODO ...
from ui.ui_base import (
    APP,
    # QtWidgets
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    # QtCore
    Qt,
    # QtGui
    QColor,
    QFont,
    QBrush,
    QPen,
    QPainter,
    QTransform,
    QRectF,
)

CHIP_MARGIN = 3
CHIP_SPACER = 10

MM2PT = 2.83464549
PT2MM = 0.3527778

# Sizes in points
A4 = (841.995, 595.35)
A3 = (1190.7, 841.995)

### -----

class GridView(QGraphicsView):
    """This is the "view" widget for the grid.
    The actual grid is implemented as a "scene".
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # Change update mode: The default, MinimalViewportUpdate, seems
        # to cause artefacts to be left, i.e. it updates too little.
        # Also BoundingRectViewportUpdate seems not to be 100% effective.
        # self.setViewportUpdateMode(
        #     QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate
        # )
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        # self.setRenderHints(
        #     QPainter.RenderHint.Antialiasing
        #     | QPainter.RenderHint.SmoothPixmapTransform
        # )
        self.setRenderHints(QPainter.RenderHint.Antialiasing)
        # self.setRenderHints(QPainter.RenderHint.TextAntialiasing)
        self.ldpi = self.logicalDpiX()
        self.pdpi = self.physicalDpiX()
        #print("LDPI:", self.ldpi)
        #print("PDPI:", self.pdpi)
# Scaling the scene by pdpi/ldpi should display the correct size ...
        #self.MM2PT = self.ldpi / 25.4
        self.setScene(QGraphicsScene())

    def pt2px(self, pt) -> int:
        px = int(self.ldpi * pt / 72.0 + 0.5)
        # print(f"pt2px: {pt} -> {px} (LDPI: {self.ldpi})")
        return px

    def px2mm(self, px):
        mm = px * 25.4 / self.ldpi
        # print(f"px2mm: {px} -> {mm} (LDPI: {self.ldpi})")
        return mm


class GridViewRescaling(GridView):
    """An QGraphicsView that automatically adjusts the scaling of its
    scene to fill the viewing window.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # Disable the scrollbars when using this resizing scheme. They
        # should not appear anyway, but this might avoid problems.
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

    def resizeEvent(self, event):
        self.rescale()
        return super().resizeEvent(event)

    def rescale(self):
        #qrect = self._sceneRect
        scene = self.scene()
        if scene:
            qrect = scene.sceneRect()
            self.fitInView(qrect, Qt.AspectRatioMode.KeepAspectRatio)


# Experimental!
class GridViewHFit(GridView):
    """A QGraphicsView that automatically adjusts the scaling of its
    scene to fill the width of the viewing window.
    """
    def __init__(self):
        super().__init__()
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        # Avoid problems at on/off transition:
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )

    def resizeEvent(self, event):
        self.rescale()
        return super().resizeEvent(event)

    def rescale(self):
        #qrect = self._sceneRect
        qrect = self.scene().sceneRect()
        size = self.size()
        vsb = self.verticalScrollBar()
        w = size.width()
# This might be problematic at the point where the scrollbar appears or
# disappears ...
# Initially the scrollbar is reported as invisible, even when it is
# clearly visible, so the calculation is wrong.
        if vsb.isVisible():
            w -= vsb.size().width()
        scale = w / qrect.width()
        t = QTransform().scale(scale, scale)
        self.setTransform(t)
#        self.fitInView(qrect, Qt.AspectRatioMode.KeepAspectRatio)


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


class Chip(QGraphicsRectItem):
    __slots__ = (
        "tag",
        "width",
        "height",
        "extras",
    )
    """A rectangular box with border colour, border width and background
    colour.
    The default fill is none (transparent), the default pen is a black
    line with width = 1 (the width of a <QPen> can be set to an <int> or
    a <float>).
    The item's coordinate system starts at (0, 0), fixed by passing
    this origin to the <QGraphicsRectItem> constructor.
    The box is then moved to the desired location using method "place".
    It can have a centred simple text item and also a text item in each
    of the four corners:
        "tl" – top left     "tr" – top right
        "bl" – bottom left  "br" – bottom right
    The font and colour of the centred text can be set separately from
    those of the corners.
    """

    def __init__(
        self,
        scene: QGraphicsScene,
        tag: str,
        width: int,
        height: int
    ):
        self.tag = tag
        self.width = width
        self.height = height
        self.extras = {}    # all the optional bits
        super().__init__(0.0, 0.0, float(width), float(height))
        scene.addItem(self)

#        self.setAcceptHoverEvents(True)

#TODO
    def hoverEnterEvent(self, event):
        print("Enter", self.tag)

    def hoverLeaveEvent(self, event):
        print("Leave", self.tag)


# Size? Would this be fixed? Quite possibly, considering the text field
# specification ... If boxed single-text items are needed, that should
# probably be another class.

# What about sizing and scaling? In QGraphicsView this is not necessarily
# a big issue, as scaling is easy. Also, it is not always clear what the
# best way to specify sizes really is. If printing to PDF is a goal, then
# something related to this (say, points or mm) might be sensible, but
# scaling to a page size is possible here, too.

# (Not really essential for this base module:) Considering a timetable
# view, something like a "pixel"-per-minute approach might make sense.
# Font scaling must always be considered, though, so using points has
# advantages too. At 8 hours per day, 1 point per minute would be 480
# points. That is not far off the width of an A4 sheet. A small scaling
# adjustment might still be necessary, but it might be a good basis.

#    font_centre = StyleCache.getFont(fontSize=FONT_CENTRE_SIZE)
#    font_corner = StyleCache.getFont(fontSize=FONT_CORNER_SIZE)

    def set_background(self, colour: str):
        """Change the background, which is initially transparent.
        This uses <StyleCache>, which accepts colours as "RRGGBB" strings.
        As a special case, calling this with an empty colour string
        produces an opaque white background.
        """
        if not colour:
            colour = "ffffff"
        self.setBrush(StyleCache.getBrush(colour))

    def set_border(self, width: int = 1, colour: str = ""):
        """Set the border width and colour, which is initially black with
        width = 1.
        This uses <StyleCache>, which accepts colours as "RRGGBB" strings.
        """
        self.setPen(StyleCache.getPen(width, colour))

    def place(self, x: int, y: int):
        """The QGraphicsItem method "setPos" takes "float" coordinates,
        either as setPos(x, y) or as setPos(QPointF). It sets the position
        of the item in parent coordinates. For items with no parent, scene
        coordinates are used.
        The position of the item describes its origin (local coordinate
        (0, 0)) in parent coordinates.
        """
        self.setPos(float(x), float(y))

    def set_text(
        self,
        text: str,
        corner: str = "c",      # default is centre
        font: str = "",
        size: int = 0,
        bold: bool = False,
        italic: bool = False,
        colour: str = "",
    ):
        try:
            text_item = self.extras[corner]
        except KeyError:
            assert corner in {"tl", "tr", "c", "bl", "br"}
            text_item = QGraphicsSimpleTextItem(text, self)
            self.extras[corner] = text_item
            text_item.setFont(StyleCache.getFont(
                family = font, size = size, bold = bold, italic = italic
            ))
            if colour:
                text_item.setBrush(StyleCache.getBrush(colour))
        else:
            # For existing items only the text can be changed
            text_item.setText(text)
        text_rect = text_item.boundingRect()
        text_width = text_rect.width()
        # Handle positioning
        if corner == "c":
            part = (self.width - CHIP_MARGIN * 2) / text_width
            if part < 1.0:
#--
                print("§???1", text_rect)
                text_item.setScale(part)
                text_rect = text_item.mapRectToParent(text_rect)
#--
                print("§???2", text_rect, text_item.boundingRect())
                text_width = text_rect.width()
            text_height = text_rect.height()
            xshift = (self.width - text_width) / 2
            yshift = (self.height - text_height) / 2
            text_item.setPos(xshift, yshift)
        else:
            w0 = self.width - CHIP_MARGIN*2 - CHIP_SPACER
            if corner[0] == "t":
                # Top of chip
                if corner == "tl":
                    xl = text_item
                    xlrect = xl.boundingRect()
                    try:
                        xr = self.extras["tr"]
                        xrrect = xr.boundingRect()
                    except KeyError:
                        xr = None
                        xrrect = QRectF()
                else:   # corner == "tr"
                    xr = text_item
                    xrrect = xr.boundingRect()
                    try:
                        xl = self.extras["tl"]
                        xlrect = xl.boundingRect()
                    except KeyError:
                        xl = None
                        xlrect = QRectF()
                xlw = xlrect.width()
                xlh = xlrect.height()
                xrw = xrrect.width()
                xrh = xrrect.height()
                part = w0 / (xlw + xrw)
                if part < 1.0:
                    if xr:
                        xr.setScale(part)
                        xrw = xr.mapRectToParent(xrrect).width()
                    if xl:
                        xl.setScale(part)
                        xlw = xl.mapRectToParent(xlrect).width()
                if xl:
                    xl.setPos(CHIP_MARGIN, CHIP_MARGIN)
                if xr:
                    xrx = self.width - CHIP_MARGIN - xrw
                    xr.setPos(xrx, CHIP_MARGIN)
            else:   # corner[0] == "b"
                # Bottom of chip
                if corner == "bl":
                    xl = text_item
                    xlrect = xl.boundingRect()
                    try:
                        xr = self.extras["br"]
                        xrrect = xr.boundingRect()
                    except KeyError:
                        xr = None
                        xrrect = QRectF()
                else:   # corner == "br"
                    xr = text_item
                    xrrect = xr.boundingRect()
                    try:
                        xl = self.extras["bl"]
                        xlrect = xl.boundingRect()
                    except KeyError:
                        xl = None
                        xlrect = QRectF()
                xlw = xlrect.width()
                xlh = xlrect.height()
                xrw = xrrect.width()
                xrh = xrrect.height()
                part = w0 / (xlw + xrw)
                if part < 1.0:
                    if xr:
                        xr.setScale(part)
                        xrr = xr.mapRectToParent(xrrect)
                        xrw = xrr.width()
                        xrh = xrr.height()
                    if xl:
                        xl.setScale(part)
                        xlr = xl.mapRectToParent(xlrect)
                        xlw = xlr.width()
                        xlh = xlr.height()
                if xl:
                    xl.setPos(CHIP_MARGIN, self.height - CHIP_MARGIN - xlh)
                if xr:
                    xrx = self.width - CHIP_MARGIN - xrw
                    xr.setPos(xrx, self.height - CHIP_MARGIN - xrh)


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



#TODO
#    def contextmenu(self, event):
#        print(f"CONTEXT MENU @ (col: {self.cell[0]} | row: {self.cell[1]})")
#        return True # propagate down (though a <Cell> should be the lowest #...)



class StyleCache:
    """Manage allocation of style resources using caches."""

    __fonts = {}  # cache for QFont items
    __brushes = {}  # cache for QBrush items
    __pens = {}  # cache for QPen items

    @classmethod
    def getPen(cls, width: int, colour: str = "") -> QPen:
        """Manage a cache for pens of different width and colour.
        <width> should be a small integer. If it is 0 a "NoPen" will
        be returned, colour being ignored.
        <colour> is a colour in the form 'RRGGBB'. If it is not supplied,
        black is assumed.
        """
        if width:
            if colour:
                assert re.match("^[0-9a-fA-F]{6}$", colour)
            else:
                colour = "000000"
            wc = (width, colour)
            try:
                return cls.__pens[wc]
            except KeyError:
                pass
            pen = QPen(QColor("#FF" + colour))
            pen.setWidth(width)
            cls.__pens[wc] = pen
            return pen
        else:
            try:
                return cls.__pens["*"]
            except KeyError:
                pen = QPen(Qt.PenStyle.NoPen)
                cls.__pens["*"] = pen
                return pen

    @classmethod
    def getBrush(cls, colour: str = "") -> QBrush:
        """Manage a cache for brushes of different colour.
        <colour> is a colour in the form 'RRGGBB'. If no colour is
        supplied, return a "non-brush" (transparent).
        """
        try:
            return cls.__brushes[colour or "*"]
        except KeyError:
            pass
        if colour:
            assert re.match("^[0-9a-fA-F]{6}$", colour)
            brush = QBrush(QColor("#FF" + colour))
            cls.__brushes[colour] = brush
        else:
            brush = QBrush()  # no fill
            cls.__brushes["*"] = brush
        return brush

    @classmethod
    def getFont(
        cls,
        family: str = "",
        size: int = 0,
        bold: bool = False,
        italic: bool = False,
    ) -> QFont:
        """Manage a cache for fonts. The font parameters are passed as
        arguments.
        """
        ftag = (family, size, bold, italic)
        try:
            return cls.__fonts[ftag]
        except KeyError:
            pass
        font = QFont()
        if family:
            font.setFamily(family)
        if size:
            font.setPointSizeF(size)
        if bold:
            font.setBold(True)
        if italic:
            font.setItalic(True)
        cls.__fonts[ftag] = font
        return font


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


#### Actually, I'm not sure what sort of scaling makes sense ...
#### Probably best to use GridViewRescaling
#    # Scaling: only makes sense if using basic, unscaled GridView
#    scale = WINDOW.pdpi / WINDOW.ldpi
#    print("§SCALING", WINDOW.pdpi, WINDOW.ldpi, scale)
#    t = QTransform().scale(scale, scale)
##    WINDOW.setTransform(t)

#TODO: Only standalone!
#    APP.setWindowIcon(QIcon(APPDATAPATH("icons/tt.svg")))
    screen = APP.primaryScreen()
    screensize = screen.availableSize()
    print("§screensize =", screensize)
    WINDOW.resize(int(screensize.width()*0.6), int(screensize.height()*0.75))
    WINDOW.show()

    return WINDOW


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    print("§§§§", APP.font().family())

    WINDOW = main(set(sys.path[1:]))
    scene = WINDOW.scene()
    A4rect = QRectF(0.0, 0.0, A4[0], A4[1])
    scene.addItem(QGraphicsRectItem(A4rect))
    WINDOW.rescale()
    c1 = Chip(scene, "CHIP_001", width = 200, height = 50)
    c1.set_text(
        "Hello, world!",
        font = "Droid Sans",
#        bold = True,
#        italic = True,
        colour = "ff0000"
    )
    c1.set_background("fff0f0")
    c1.place(20, 50)
    c2 = Chip(scene, "CHIP_002", width = 200, height = 50)
    c2.set_text(
        "Il: Much, much more than just a Hello, world!",
#        font = "Droid Sans",
        bold = True,
#        italic = True,
        colour = "ff0000"
    )
    c2.set_background("fff0f0")
    c2.set_text("TOP LEFT is a really great place to be", "tl")
    c2.set_text("TOP RIGHT and a lot more", "tr")
    c2.set_text("BOTTOM LEFT", "bl")
    c2.set_text("BOTTOM RIGHT", "br")
    c2.place(40, 90)
    sys.exit(APP.exec())
