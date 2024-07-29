"""
show_room.py

Last updated:  2024-07-29

Populate a timetable grid with the lessons in a prticular room.


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

### +++++

from timetable_grid import Tile

### -----


def show_room(data, grid, room):
    activities = data.room_activities[room]
    for ai in activities:
        a = data.data.activities[ai]
        tile = Tile(
            canvas = grid,
            tag = f"{room}:{ai}",  # tile tag (id)
            duration = a["Duration"],   # number of periods
            divs = 1,           # total cell divisions
            div0 = 0,           # starting division
            ndivs = 1,          # cell divisions for this tile
            text = ",".join(a["Students"]),   # central text
            bg = "FFF0E0", # background colour ("RRGGBB", default transp.)
            tl = a["Subject"],
            br = ",".join(a["Teachers"]),
            bl = "!" if a["Fixed"] else ""
        )
        grid.place_tile(tile, day = a["Day"], period = a["Hour"])


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from PySide6.QtWidgets import (
        QGraphicsRectItem,
        QGraphicsView,
        QGraphicsSimpleTextItem,
    )
    from PySide6.QtCore import QRectF

    from timetable_grid import GridView
    from canvas import StyleCache, A4
    from read_fet_results import FetData
    from view_part_info import ViewPartInfo
    from ui_base import init_app, run
    init_app()

#TODO: How to get the data???
    source = "test_data_and_timetable.fet"
    #source = "test_data_1.fet"
    fet_data = FetData(source)
    #print("\n§DAYS:", fet_data.days)
    #print("\n§HOURS:", fet_data.hours)
    #print("\n§CLASSES:", fet_data.classes)
    #print("\n§ROOMS:", fet_data.rooms)
    #for ai, a in fet_data.activities.items():
    #    print(f"\n§ACTIVITY {ai:04d}: {a}")

    vpi = ViewPartInfo(fet_data)

    grid = GridView(QGraphicsView(), fet_data.hours, fet_data.days)
    _scene = grid.view.scene()
    scene_rect = _scene.sceneRect()

    #frame = QGraphicsRectItem(scene_rect.adjusted(-5.0, -5.0, 5.0, 5.0))
    #frame.setPen(StyleCache.getPen(0))
    #_scene.addItem(frame)

    #A4rect = QGraphicsRectItem(QRectF(0.0, 0.0, *A4))
    #A4rect.setPen(StyleCache.getPen(width = 3, colour = "FF0000"))
    #_scene.addItem(A4rect)


    HEADER_MARGIN = 50 # ???
    w0, h0 = A4
    w = scene_rect.width()
    h = scene_rect.height()
    print("§ SCENE DIMS:", w, w0, h, h0)
    dw = (w0 - w) / 2
    dh = (h0 - h - HEADER_MARGIN) / 2
    assert dw > 0 and dh > 0
    y0 = scene_rect.top() - HEADER_MARGIN
    x0 = scene_rect.left()

    header_font = StyleCache.getFont(size = 14, bold = True)
    header = QGraphicsSimpleTextItem()
    header.setFont(header_font)
    header.setPos(x0 + 30, y0 + HEADER_MARGIN/2 - 7)
    _scene.addItem(header)

    A4rect = QGraphicsRectItem(QRectF(x0 - dw, y0 - dh, *A4))
    A4rect.setPen(StyleCache.getPen(width = 3, colour = "FF0000"))
    _scene.addItem(A4rect)

    screen = qApp.primaryScreen()
    screensize = screen.availableSize()
    print("§screensize =", screensize)
    grid.view.resize(
        int(screensize.width()*0.6),
        int(screensize.height()*0.75)
    )
    grid.view.show()

    r = "eOS"
    show_room(vpi, grid, r)
    ln = fet_data.rooms[r]["LongName"]
    if ln:
        htext = f"Raum {r} ({ln})"
    else:
        htext = f"Raum {r}"
    header.setText(htext)

    run()
