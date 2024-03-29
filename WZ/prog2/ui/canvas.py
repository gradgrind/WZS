"""
ui/canvas.py

Last updated:  2024-03-29

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
    QWidget,

    QMenu,
    # QtCore
    Qt,
    QEvent,
    QObject,
    QTimer,
    # QtGui
    QColor,
    QFont,
    QBrush,
    QPen,
    QPainter,
    QTransform,
    QRectF,
    # other
    HoverRectItem,
    EventFilter,
)

CHIP_MARGIN = 2
CHIP_SPACER = 10

MM2PT = 2.83464549
PT2MM = 0.3527778

# Sizes in points
A4 = (841.995, 595.35)
A3 = (1190.7, 841.995)

### -----


class Canvas:
    """This is the "view" widget for the canvas.
    The actual canvas is implemented as a "scene".
    """
    def __init__(self, view: QGraphicsView):
        self.view = view
        # Change update mode: The default, MinimalViewportUpdate, seems
        # to cause artefacts to be left, i.e. it updates too little.
        # Also BoundingRectViewportUpdate seems not to be 100% effective.
        # view.setViewportUpdateMode(
        #     QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate
        # )
        view.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        # view.setRenderHints(
        #     QPainter.RenderHint.Antialiasing
        #     | QPainter.RenderHint.SmoothPixmapTransform
        # )
        view.setRenderHints(QPainter.RenderHint.Antialiasing)
        # view.setRenderHints(QPainter.RenderHint.TextAntialiasing)
        self.ldpi = view.logicalDpiX()
        self.pdpi = view.physicalDpiX()
        #print("LDPI:", self.ldpi)
        #print("PDPI:", self.pdpi)
# Scaling the scene by pdpi/ldpi should display the correct size ...
        #self.MM2PT = self.ldpi / 25.4

#TODO: change to use straight QGraphicsScene
        self.scene = CanvasScene(view)
        #view.setScene(self.scene)

    def pt2px(self, pt) -> int:
        px = int(self.ldpi * pt / 72.0 + 0.5)
        # print(f"pt2px: {pt} -> {px} (LDPI: {self.ldpi})")
        return px

    def px2mm(self, px):
        mm = px * 25.4 / self.ldpi
        # print(f"px2mm: {px} -> {mm} (LDPI: {self.ldpi})")
        return mm


class CanvasRescaling(Canvas):
    """A QGraphicsView that automatically adjusts the scaling of its
    scene to fill the viewing window.
    """
    def __init__(self, view):
        super().__init__(view)
        # Disable the scrollbars when using this resizing scheme. They
        # should not appear anyway, but this might avoid problems.
        view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.event_filter = EventFilter(view, self.event_handler)

    def event_handler(self, w: QWidget, event: QEvent):
        if event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self.rescale)
        return False

    def rescale(self):
        scene = self.view.scene()
        qrect = scene.sceneRect()
        self.view.fitInView(qrect, Qt.AspectRatioMode.KeepAspectRatio)


class CanvasHFit(Canvas):
    """A QGraphicsView that automatically adjusts the scaling of its
    scene to fill the width of the viewing window.
    """
    def __init__(self, view):
        super().__init__(view)
        view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        # Avoid glitches / problems at on/off transition:
        view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.event_filter = EventFilter(view, self.event_handler)

    def event_handler(self, w: QWidget, event: QEvent):
        if event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self.rescale)
        return False

    def rescale(self):
        view = self.view
        scene = view.scene()
        qrect = scene.sceneRect()
        size = view.size()
        vsb = view.verticalScrollBar()
        w = size.width()
# This might be problematic at the point where the vertical scrollbar
# appears or disappears, so a permanent scrollbar is recommended.
        if vsb.isVisible():
            w -= vsb.size().width()
        scale = w / qrect.width()
        t = QTransform().scale(scale, scale)
        view.setTransform(t)


#TODO: features not yet settled
class CanvasScene:
    def __init__(self, view):
        self._scene = QGraphicsScene()
        view.setScene(self._scene)
        self.items = {}
        self.event_filter = EventFilter(self._scene, self.event_handler)
        self.make_context_menu()

    def event_handler(self, obj: QObject, event: QEvent):
        et = event.type()
        if et == QEvent.Type.GraphicsSceneMousePress:
            self.mouse_press_event(event)
            return True
        if et == QEvent.Type.GraphicsSceneContextMenu:
            self.context_menu_event(event)
            return True
        return False

    def add_item(self, item, tag):
        self.items[tag] = item
        self._scene.addItem(item._item)

    def make_context_menu(self):
        self.context_menu = QMenu()
        Action = self.context_menu.addAction("I am context Action 1")
        Action.triggered.connect(self.context_1)

    def mouse_press_event(self, event):
        point = event.scenePos()
        items = self._scene.items(point)
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
                        cell = item.tag
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
                if item0:
                    print(f"Left press{shift}{ctrl}{alt} @ {cell}")
# Note that ctrl-click is for context menu on OSX ...
# Note that alt-click is intercepted by some window managers on Linux ...
                    if shift:
#???
                        self.place_tile("T2", cell)
                    if alt:
                        self.select_cell(cell)

    def context_menu_event(self, event):
        point = event.scenePos()
        items = self._scene.items(point)
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


class Chip:
    __slots__ = (
        "_item",
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
        canvas: Canvas,
        tag: str,
        width: float,
        height: float,
        hover = None,
    ):
        self.width = width
        self.height = height
        self.extras = {}    # all the optional bits
        self._item = HoverRectItem(
            0.0, 0.0, width, height,
            hover = hover
        )
        self._item.tag = tag
        canvas.scene.add_item(self, tag)

# Size? Would this be fixed? Quite possibly, considering the text field
# specification ... If boxed single-text items are needed, that should
# probably be another class.
#TODO:
# However, when using multiple-period tiles, it is possible that the
# size changes. In this case it would be necessary to recalculate all the
# text fields.

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

    def set_background(self, colour: str):
        """Change the background, which is initially transparent.
        This uses <StyleCache>, which accepts colours as "RRGGBB" strings.
        As a special case, calling this with an empty colour string
        produces an opaque white background.
        """
        if not colour:
            colour = "ffffff"
        self._item.setBrush(StyleCache.getBrush(colour))

    def set_border(self, width: float = None, colour: str = None):
        """Set the border width and colour, which is initially black with
        width = 1.
        This uses <StyleCache>, which accepts colours as "RRGGBB" strings.
        """
        if width:
            self._item.setPen(StyleCache.getPen(width, colour))
        elif colour:
            self._item.setPen(StyleCache.getPen(1.0, colour))
        else:
            self._item.setPen(StyleCache.getPen())

    def place(self, x: float, y: float, w: float = None, h: float = None):
        """The QGraphicsItem method "setPos" takes "float" coordinates,
        either as setPos(x, y) or as setPos(QPointF). It sets the position
        of the item in parent coordinates. For items with no parent, scene
        coordinates are used.
        The position of the item describes its origin (local coordinate
        (0, 0)) in parent coordinates.
        The size of the chip can be changed by supplying new width and/or
        height values.
        """
        self._item.setPos(x, y)
        if w is None:
            if h is None:
                return
            self.height = h
        elif h is None:
            self.width = w
        else:
            self.height = h
            self.width = w
        # Handle the text field placement and potential shrinking
        c = self.extras.get("c")
        if c:
            self._set_centre_text(c)
        tl = self.extras.get("tl")
        tr = self.extras.get("tr")
        if tl or tr:
            self._set_top_text(tl, tr)
        bl = self.extras.get("bl")
        br = self.extras.get("br")
        if bl or br:
            self._set_bottom_text(bl, br)

    def set_text(
        self,
        text: str,
        corner: str = "c",      # default is centre
        font: str = "",
        size: float = None,
        bold: bool = False,
        italic: bool = False,
        colour: str = "",
    ):
        try:
            text_item = self.extras[corner]
        except KeyError:
            assert corner in {"tl", "tr", "c", "bl", "br"}
            text_item = QGraphicsSimpleTextItem(text, self._item)
            self.extras[corner] = text_item
            text_item.setFont(StyleCache.getFont(
                family = font, size = size, bold = bold, italic = italic
            ))
            if colour:
                text_item.setBrush(StyleCache.getBrush(colour))
        else:
            # For existing items only the text can be changed
            text_item.setText(text)
        if corner == "c":
            self._set_centre_text(text_item)
        elif corner == "tl":
            self._set_top_text(text_item, self.extras.get("tr"))
        elif corner == "bl":
            self._set_bottom_text(text_item, self.extras.get("br"))
        elif corner == "tr":
            self._set_top_text(self.extras.get("tl"), text_item)
        elif corner == "br":
            self._set_bottom_text(self.extras.get("bl"), text_item)

    def _set_centre_text(self, text_item):
        text_rect = text_item.boundingRect()
        text_width = text_rect.width()
        part = (self.width - CHIP_MARGIN * 2) / text_width
        if part < 1.0:
            text_item.setScale(part)
            text_rect = text_item.mapRectToParent(text_rect)
            text_width = text_rect.width()
        text_height = text_rect.height()
        xshift = (self.width - text_width) / 2
        yshift = (self.height - text_height) / 2
        text_item.setPos(xshift, yshift)

    def _set_top_text(self, xl, xr):
        w0 = self.width - CHIP_MARGIN*2 - CHIP_SPACER
        if xl:
            xlrect = xl.boundingRect()
        else:
            xlrect = QRectF()
        if xr:
            xrrect = xr.boundingRect()
        else:
            xrrect = QRectF()
        xlw = xlrect.width()
        #xlh = xlrect.height()
        xrw = xrrect.width()
        #xrh = xrrect.height()
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

    def _set_bottom_text(self, xl, xr):
        w0 = self.width - CHIP_MARGIN*2 - CHIP_SPACER
        if xl:
            xlrect = xl.boundingRect()
        else:
            xlrect = QRectF()
        if xr:
            xrrect = xr.boundingRect()
        else:
            xrrect = QRectF()
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
            xl.setPos(CHIP_MARGIN, self.height - CHIP_MARGIN - xlh)
        if xr:
            xrx = self.width - CHIP_MARGIN - xrw
            xr.setPos(xrx, self.height - CHIP_MARGIN - xrh)

# May be useful (to get screen coordinates)?
#def get_pos(view, item, point):
#        scenePos = item.mapToScene(point)
#        viewportPos = view.mapFromScene(scenePos)
#        viewPos = view.viewport().mapToParent(viewportPos)
#        globalViewPos = view.mapToGlobal(QPoint(0, 0))
#        return globalViewPos.x + viewPos.x, globalViewPos.y + viewPos.y


class StyleCache:
    """Manage allocation of style resources using caches."""

    __fonts = {}  # cache for QFont items
    __brushes = {}  # cache for QBrush items
    __pens = {}  # cache for QPen items

    @classmethod
    def getPen(cls, width: float = None, colour: str = None) -> QPen:
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
            pen.setWidthF(width)
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
        family: str = None,
        size: float = None,
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
    WINDOW = QGraphicsView()
    window = CanvasRescaling(WINDOW)
    #window = CanvasHFit(WINDOW)
    #window = Canvas(WINDOW)

    return window

#### Actually, I'm not sure what sort of scaling makes sense ...
#### Probably best to use GridViewRescaling
#    # Scaling: only makes sense if using basic, unscaled GridView
#    scale = WINDOW.pdpi / WINDOW.ldpi
#    print("§SCALING", WINDOW.pdpi, WINDOW.ldpi, scale)
#    t = QTransform().scale(scale, scale)
##    WINDOW.setTransform(t)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    print("§§§§", APP.font().family())

    def test_hover(item, enter):
        print("§HOVER:", item.tag, enter)

    canvas = main(set(sys.path[1:]))
    _scene = canvas.view.scene()
    A4rect = QRectF(0.0, 0.0, A4[0], A4[1])
    _scene.addItem(QGraphicsRectItem(A4rect))
    frame = QGraphicsRectItem(A4rect.adjusted(-5.0, -5.0, 5.0, 5.0))
    frame.setPen(StyleCache.getPen())
    _scene.addItem(frame)
#    scene = canvas.scene
    c1 = Chip(
        canvas, "CHIP_001", width = 200, height = 50, hover = test_hover
    )
    c1.set_text(
        "Hello, world!",
        font = "Droid Sans",
#        bold = True,
#        italic = True,
        colour = "ff0000"
    )
    c1.set_background("fff0f0")
    c1.place(20, 50)
    c2 = Chip(canvas, "CHIP_002", width = 200, height = 50)
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

    screen = APP.primaryScreen()
    screensize = screen.availableSize()
    print("§screensize =", screensize)
    canvas.view.resize(
        int(screensize.width()*0.6),
        int(screensize.height()*0.75)
    )
    canvas.view.show()

    sys.exit(APP.exec())
