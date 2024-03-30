"""
ui/timetable_grid.py

Last updated:  2024-03-30

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

if __name__ == "__main__":
    import sys, os
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

### +++++

from ui.ui_base import (
    APP,
    # QtWidgets
    QGraphicsRectItem,
    QGraphicsLineItem,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    # QtGui
    # QtCore
)
from ui.canvas import (
    Canvas,
    CanvasRescaling,
    StyleCache,
    Chip,
    CHIP_MARGIN,
)

_DAYWIDTH = 140.0
_VHEADERWIDTH = 80.0
_HHEADERHEIGHT = 40.0
_GRIDLINEWIDTH = 1.0
_GRIDLINECOLOUR = 'b0b0b0'

# Fonts
FONT_CENTRE_SIZE = 12
FONT_CORNER_SIZE = 8

### -----


class Tile(Chip):
    __slots__ = (
        "duration",
        "divs",
        "div0",
        "ndivs",
    )
    # Note that a "lesson" might need more than one tile – if the constituent
    # groups are not contiguous in the display cell.

    def __init__(
        self,
        canvas: Canvas,
        tag: str,               # tile tag (id)
        duration: int,          # number of periods
        divs: int,              # total cell divisions
        div0: int,              # starting division
        ndivs: int,             # cell divisions for this tile
        text: str,              # central text
        bg: str = None,         # background colour ("RRGGBB", default white)
        **corners               # corner texts {pos: text}
    ):
        self.duration = duration
        self.divs = divs
        self.div0 = div0
        self.ndivs = ndivs
        super().__init__(
            canvas, tag, width = 100.0, height = 100.0,
            hover = None,
        )
        if bg:
            self.set_background(bg)
        self.set_text(text, size = FONT_CENTRE_SIZE, no_place = True)
        for k, v in corners.items():
            self.set_text(v, k, size = FONT_CORNER_SIZE, no_place = True)
        #self.setZValue(5)
#?
#        self.hide()


class GridView(CanvasRescaling):
    def __init__(self, view: QGraphicsView, period_times, days):
        super().__init__(view)
        _scene = view.scene()
        # Determine the vertical grid cells using the period times and days
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
        # Determine the horizontal grid cells using <_DAYWIDTH>
        dlines = []
        d0 = 0.0
        for tag in days:
            d1 = d0 + _DAYWIDTH
            dlines.append((d0, d1))
            d0 = d1
        #print("???", dlines)

        w0 = dlines[-1][1]
        h0 = hlines[-1][1]
        width = w0 + _VHEADERWIDTH
        height = h0 + _HHEADERHEIGHT
        weekbox = QGraphicsRectItem(
            -_VHEADERWIDTH, -_HHEADERHEIGHT, width, height
        )
        _scene.addItem(weekbox)
        weekbox.setPen(StyleCache.getPen(_GRIDLINEWIDTH))
        weekbox.setZValue(10)
        x0 = None
        for x01 in dlines:
            for x in x01:
                if x == x0:
                    continue
                else:
                    x0 = x
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
        y0 = None
        for y01 in hlines:
            for y in y01:
                if y == y0:
                    continue
                else:
                    y0 = y
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
            x0 = dlines[i][0]
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

    def place_tile(self, tile: Tile, day: int, period: int):
        x0, x1 = self.xlines[day]
        w = x1 - x0
        y0, y1 = self.ylines[day]
        if tile.duration > 1:
            y1 = self.ylines[day + tile.duration - 1][1]
        h = y1 - y0

        offset = w * tile.div0 / tile.divs
        extent = w * tile.ndivs / tile.divs
        tile.place(
            x0 + offset + _GRIDLINEWIDTH,
            y0 + _GRIDLINEWIDTH,
            extent - _GRIDLINEWIDTH * 2,
            h - _GRIDLINEWIDTH * 2
        )


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

    grid = GridView(QGraphicsView(), PERIOD_TIMES, DAYS)
    _scene = grid.view.scene()
    scene_rect = _scene.sceneRect()
    frame = QGraphicsRectItem(scene_rect.adjusted(-5.0, -5.0, 5.0, 5.0))
    frame.setPen(StyleCache.getPen(0))
    _scene.addItem(frame)
#    A4rect = QRectF(0.0, 0.0, A4[0], A4[1])
#    _scene.addItem(QGraphicsRectItem(A4rect))
#    scene = grid.scene

    tile = Tile(
        canvas = grid,
        tag = "tile_01",    # tile tag (id)
        duration = 1,       # number of periods
        divs = 1,           # total cell divisions
        div0 = 0,           # starting division
        ndivs = 1,          # cell divisions for this tile
        text = "TILE 01",   # central text
        bg = "FFF0E0",      # background colour ("RRGGBB", default white)
    )
    grid.place_tile(tile, day = 1, period = 2)

    tile = Tile(
        grid, "tile_02", 1, 3, 1, 1, "TILE 02", "F0E0FF",
        tl = "tl", tr = "tr", bl = "bl", br = "br"
    )
    grid.place_tile(tile, 2, 3)
    tile = Tile(
        grid, "tile_03", 2, 3, 2, 1, "TILE 03", "E0F0FF",
        tl = "AW", br = "yp"
    )
    grid.place_tile(tile, 2, 3)

    screen = APP.primaryScreen()
    screensize = screen.availableSize()
    print("§screensize =", screensize)
    grid.view.resize(
        int(screensize.width()*0.6),
        int(screensize.height()*0.75)
    )
    grid.view.show()

    sys.exit(APP.exec())
