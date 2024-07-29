"""
view_part_info.py

Last updated:  2024-07-29

Gather the basic information needed to populate a timetable grid with
the lessons of a single class, teacher or room.


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

### -----


def cg2c_g(students: str) -> tuple[str, str]:
    """Split a class[.group] into (class, group or "").
    """
    try:
        c, g = students.split(CLASS_GROUP_SEP, 1)
        return (c, g)
    except ValueError:
        return (students, "")


class ViewPartInfo:
    def __init__(self, data):
        self.data = data
        self.class_divs = self.divide_classes()
        self.class_activities = self.class_activity_tiles()
        # Gather activities for each teacher and each room
        self.teacher_activities = {}
        self.room_activities = {}
        for ai, a in self.data.activities.items():
            for t in a["Teachers"]:
                try:
                    self.teacher_activities[t].append(ai)
                except KeyError:
                    self.teacher_activities[t] = [ai]
            r = a["Room"]
            rg = self.data.rooms[r]["RoomGroups"]
            if not rg:
                rg = [r]
            for r in rg:
                try:
                    self.room_activities[r].append(ai)
                except KeyError:
                    self.room_activities[r] = [ai]

    def divide_classes(self):
        """Build a group -> (division, index) mapping for each class.
        """
        cl_divs = {}
        for cl, div_groups in self.data.classes.items():
            cl_divs[cl] = {
                g: (d, i)
                for d, glist in enumerate(div_groups)
                for i, g in enumerate(glist)
            }
        return cl_divs

    def class_tiles(self, students: list
    ) -> dict[str, tuple[int, list[tuple[int, str]]]]:
        """Build the basic information required for constructing group
        tiles for the class view.
        Each cell is divided according to the groups within a class
        division which are covered by the lesson tile.
        The result provides the division index (-1 => whole class) and
        the included groups (index within the division, name tag) as
        a list.
        """
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

    def class_activity_tiles(self) -> dict[str, list[int]]:
        """Prepare the basic size and offset information for the tiles
        in a class view.
        The tile size/offset info is added to each activity.
        Return a mapping, class -> list of activity indexes.
        """
        class_activities = {}  # class -> activities
        for ai, a in self.data.activities.items():
            smap = self.class_tiles(a["Students"])
            atiles = {}
            for c, dgs in smap.items():
                try:
                    class_activities[c].append(ai)
                except KeyError:
                    class_activities[c] = [ai]
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
            a["Class_Tiles"] = atiles
        return class_activities


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from read_fet_results import FetData
#    from ui_base import init_app, run
#    init_app()

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
    for cl, td in vpi.class_divs.items():
        print("\n$ CLASS", cl, td)
        print("   -->", vpi.class_activities[cl])

    for t, ailist in vpi.teacher_activities.items():
        print("\n$ TEACHER", t, ailist)

    for r, ailist in vpi.room_activities.items():
        print("\n$ ROOM", r, ailist)
