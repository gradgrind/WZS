"""
timetable_viewer.py

Last updated:  2024-07-29

Gui to show the timetable of a class, a teacher or a room.


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

from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QListWidget,
    QGraphicsView,
)
from view_part_info import ViewPartInfo
from show_class import show_class
from show_room import show_room
from show_teacher import show_teacher

### -----


class TimetableViewer(QWidget):
    def __init__(self, data, parent = None):
        self.data = ViewPartInfo(data)
        super().__init__(parent)

        hbox = QHBoxLayout(self)
        gview = QGraphicsView()
        hbox.addWidget(gview)

        vbox = QVBoxLayout()
        hbox.addLayout(vbox)
        viewtype = QFrame()
        vbox.addWidget(viewtype)
        bbox = QVBoxLayout(viewtype)
        choose_class = QRadioButton("Klasse")
        bbox.addWidget(choose_class)
        choose_class.toggled.connect(self.show_classes)
        choose_teacher = QRadioButton("Lehrer")
        bbox.addWidget(choose_teacher)
        choose_teacher.toggled.connect(self.show_teachers)
        choose_room = QRadioButton("Raum")
        bbox.addWidget(choose_room)
        choose_room.toggled.connect(self.show_rooms)
        self.choice = QListWidget()
        self.choice.setFixedWidth(200)
        self.choice.currentItemChanged.connect(self.select_item)
        vbox.addWidget(self.choice)

        self.showing = -1 # 0: classes, 1: teachers, 2: rooms

        self.grid = GridView(gview, data.hours, data.days)
        _scene = self.grid.view.scene()
        scene_rect = _scene.sceneRect()
        HEADER_MARGIN = 50 # ???
        w0, h0 = A4
        w = scene_rect.width()
        h = scene_rect.height()
        #print("§ SCENE DIMS:", w, w0, h, h0)
        dw = (w0 - w) / 2
        dh = (h0 - h - HEADER_MARGIN) / 2
        assert dw > 0 and dh > 0
        y0 = scene_rect.top() - HEADER_MARGIN
        x0 = scene_rect.left()

        header_font = StyleCache.getFont(size = 14, bold = True)
        self.header = QGraphicsSimpleTextItem()
        self.header.setFont(header_font)
        self.header.setPos(x0 + 30, y0 + HEADER_MARGIN/2 - 7)
        _scene.addItem(self.header)

        A4rect = QGraphicsRectItem(QRectF(x0 - dw, y0 - dh, *A4))
        A4rect.setPen(StyleCache.getPen(width = 3, colour = "FF0000"))
        _scene.addItem(A4rect)

    def show_classes(self, on):
        if not on:
            return
        self.choice.clear()
        self.header.setText("–––")
        self.choice.addItems(list(self.data.data.classes))
        self.showing = 0

    def show_teachers(self, on):
        if not on:
            return
        self.choice.clear()
        self.header.setText("–––")
        tlist = [
            t for t in self.data.data.teachers
            if t in self.data.teacher_activities
        ]
        self.choice.addItems(tlist)
        self.showing = 1

    def show_rooms(self, on):
        if not on:
            return
        self.choice.clear()
        self.header.setText("–––")
        rlist = [
            r for r in self.data.data.rooms
            if r in self.data.room_activities
        ]
        self.choice.addItems(rlist)
        self.showing = 2

    def select_item(self, lwitem):
        if not lwitem:
            self.grid.scene.clear_items()
            return
        if self.showing == 0:
            self.select_class(lwitem)
        elif self.showing == 1:
            self.select_teacher(lwitem)
        elif self.showing == 2:
            self.select_room(lwitem)

    def select_class(self, lwitem):
        self.grid.scene.clear_items()
        c = lwitem.text()
        show_class(self.data, self.grid, c)
        self.header.setText(f"Klasse {c}")

    def select_teacher(self, lwitem):
        self.grid.scene.clear_items()
        t = lwitem.text()
        show_teacher(self.data, self.grid, t)
        self.header.setText(f"{self.data.data.teachers[t]} ({t})")

    def select_room(self, lwitem):
        self.grid.scene.clear_items()
        r = lwitem.text()
        show_room(self.data, self.grid, r)
        ln = self.data.data.rooms[r]["LongName"]
        if ln:
            htext = f"Raum {r} ({ln})"
        else:
            htext = f"Raum {r}"
        self.header.setText(htext)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from PySide6.QtWidgets import (
        QGraphicsRectItem,
        QGraphicsView,
        QGraphicsSimpleTextItem,
    )
    from PySide6.QtCore import QRectF

    from timetable_grid import GridView, Tile
    from canvas import StyleCache, A4
    from read_fet_results import FetData
    from ui_base import init_app, run
    init_app()

#TODO: How to get the data???
    source = "test_data_and_timetable.fet"
    #source = "testx_data_and_timetable.fet"
    fet_data = FetData(source)
    #print("\n§DAYS:", fet_data.days)
    #print("\n§HOURS:", fet_data.hours)
    #print("\n§CLASSES:", fet_data.classes)
    #print("\n§ROOMS:", fet_data.rooms)
    #for ai, a in fet_data.activities.items():
    #    print(f"\n§ACTIVITY {ai:04d}: {a}")

#    clview = ClassView(fet_data)
#    for cl, td in clview.class_divs.items():
#        print("$ ++", cl, td)

#    for ai, a in clview.data.activities.items():
#        print(f"\n§ACTIVITY {ai:04d}: {a}\n")

    tview = TimetableViewer(fet_data)
    tview.show()
    run()

    quit(1)

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

    show_class(clview, grid, "12")

    run()
