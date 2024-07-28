"""
ui/modules/show_class.py

Last updated:  2024-07-27

Populate a timetable grid with the lessons of a class.


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

from read_fet_results import CLASS_GROUP_SEP



def tile_divisions(div_groups: list[list[str]]):
    # Gather division components
    g2d = {
        g: (d, i)
        for d, glist in enumerate(div_groups)
        for i, g in enumerate(glist)
    }
    return g2d


def cg2c_g(students: str) -> tuple[str, str]:
    """Split a class[.group] into (class, group or "").
    """
    try:
        c, g = students.split(CLASS_GROUP_SEP, 1)
        return (c, g)
    except ValueError:
        return (students, "")


class ClassView:
    def __init__(self, data):
        self.data = data
        self.class_divs = self.divide_classes()
        self.activity_tiles()

    def divide_classes(self):
        cl_divs = {}
        for cl, dg in self.data.classes.items():
            td = tile_divisions(dg)
            cl_divs[cl] = td
        return cl_divs

    def class_tiles(self, students: list
    ) -> dict[str, tuple[int, list[tuple[int, str]]]]:
        cl_tiles = {}
        for s in students:
            cl, g = cg2c_g(s)
            if g:
                d, i = self.class_divs[cl][g]
                try:
                    divdata = cl_tiles[cl]
                except KeyError:
                    cl_tiles[cl] = (d, [(i, g)])
                else:
                    assert divdata[0] == d and i not in divdata[1]
                    divdata[1].append((i, g))
            else:
                assert cl not in cl_tiles
                cl_tiles[cl] = (-1, [(0, "")])
        return cl_tiles

    def activity_tiles(self):
        self.class_activities = {}  # class -> activities
        for ai, a in self.data.activities.items():
            smap = self.class_tiles(a["Students"])
            atiles = {}
            for c, dgs in smap.items():
                try:
                    self.class_activities[c].append(ai)
                except KeyError:
                    self.class_activities[c] = [ai]
                div, groups = dgs
                if div < 0:
                    # offset, number of groups, total number of groups, group
                    atiles[c] = [(0, 1, 1, [])]
                    continue
                total = len(self.data.classes[c][div])
                parts = []
                p0 = 0
                l = 0
                gl = []
                for p, g in sorted(groups):
                    if p == (p0 + l):
                        l += 1
                        gl.append(g)
                    else:
                        if l != 0:
                            parts.append((p0, l, total, gl))
                        p0 = p
                        l = 1
                        gl = [g]
                if l != 0:
                    parts.append((p0, l, total, gl))
                atiles[c] = parts
            a["Tiles"] = atiles


def show_class(data, grid, klass):
    activities = data.class_activities[klass]
    for ai in activities:
        a = data.data.activities[ai]
        for o, l, t, gl in a["Tiles"][klass]:
            rrooms = a["Real_Rooms"]
            if rrooms:
                if len(rrooms) > 4:
                    room = ",".join(rrooms[:3]) + " ..."
                else:
                    room = ",".join(rrooms)
            else:
                room = a["Room"]
            tile = Tile(
                canvas = grid,
                tag = f"{klass}:{ai},{o}",  # tile tag (id)
                duration = a["Duration"],   # number of periods
                divs = t,           # total cell divisions
                div0 = o,           # starting division
                ndivs = l,          # cell divisions for this tile
                text = a["Subject"],   # central text
                bg = "FFF0E0", # background colour ("RRGGBB", default transp.)
                tl = ",".join(a["Teachers"]),
                tr = ",".join(gl),
                bl = room,
                br = "!" if a["Fixed"] else ""
            )
            grid.place_tile(tile, day = a["Day"], period = a["Hour"])


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from PySide6.QtWidgets import (
        QGraphicsRectItem,
        QGraphicsView,
    )

    from timetable_grid import GridView, Tile
    from canvas import StyleCache
    from read_fet_results import FetData
    from ui_base import init_app, run
    init_app()

#TODO: How to get the data???
    source = "test_data_and_timetable.fet"
    source = "test_data_1.fet"
    fet_data = FetData(source)
    #print("\n§DAYS:", fet_data.days)
    #print("\n§HOURS:", fet_data.hours)
    #print("\n§CLASSES:", fet_data.classes)
    #print("\n§ROOMS:", fet_data.rooms)
    #for ai, a in fet_data.activities.items():
    #    print(f"\n§ACTIVITY {ai:04d}: {a}")

    clview = ClassView(fet_data)
    for cl, td in clview.class_divs.items():
        print("$ ++", cl, td)

    for ai, a in clview.data.activities.items():
        print(f"\n§ACTIVITY {ai:04d}: {a}\n")



    #quit(1)

    grid = GridView(QGraphicsView(), fet_data.hours, fet_data.days)
    _scene = grid.view.scene()
    scene_rect = _scene.sceneRect()
    frame = QGraphicsRectItem(scene_rect.adjusted(-5.0, -5.0, 5.0, 5.0))
    frame.setPen(StyleCache.getPen(0))
    _scene.addItem(frame)
#    A4rect = QRectF(0.0, 0.0, A4[0], A4[1])
#    _scene.addItem(QGraphicsRectItem(A4rect))
#    scene = grid.scene


    screen = qApp.primaryScreen()
    screensize = screen.availableSize()
    print("§screensize =", screensize)
    grid.view.resize(
        int(screensize.width()*0.6),
        int(screensize.height()*0.75)
    )
    grid.view.show()

    show_class(clview, grid, "12")

    run()
