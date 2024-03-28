#TODO: add teacher view, editing
"""
ui/modules/timetable_editor.py

Last updated:  2023-09-16

Show a timetable grid and allow placement of lesson tiles.


=+LICENCE=============================
Copyright 2023 Michael Towers

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
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))
#    from core.base import start
    from ui.ui_base import StandalonePage as Page
#    start.setup(os.path.join(basedir, 'TESTDATA'))
else:
    from ui.ui_base import StackPage as Page

T = TRANSLATIONS("ui.modules.timetable_editor")

### +++++

from ui.timetable_grid import GridPeriodsDays
from core.basic_data import (
    get_database,
    CONFIG,
    CALENDAR,

    clear_cache,
    get_days,
    get_periods,
    get_classes,
    GROUP_ALL,
    get_teachers,
    NO_TEACHER,
    get_rooms,
    timeslot2index,
)
from timetable.tt_basic_data import TimetableData
from ui.ui_base import (
    ### QtWidgets:
    QListWidgetItem,
    QTableWidgetItem,
    QMenu,
    ### QtGui:
    ### QtCore:
    Qt,
#    QEvent,
    Slot,
    ### uic
    uic,
)

WHOLE_CLASS = ""
#WHOLE_CLASS = GROUP_ALL

### -----

def init():
    MAIN_WIDGET.add_tab(TimetableEditor())


class TimetableEditor(Page):
    def __init__(self):
        super().__init__()
        uic.loadUi(APPDATAPATH("ui/timetable_view.ui"), self)

    def enter(self):
        open_database()
        clear_cache()
        self.TT_CONFIG = MINION(DATAPATH("CONFIG/TIMETABLE"))
        tt = TimetableManager()
        self.timetable = tt
        breaks = self.TT_CONFIG["BREAKS_BEFORE_PERIODS"]
        self.grid = WeekGrid(breaks)
        self.table_view.setScene(self.grid)
        tt.set_gui(self)

        ## Set up class list
        self.all_classes = []
        self.class_list.clear()
        for k, name in get_classes().get_class_list():
            if tt.tt_data.class_ttls.get(k):
                self.all_classes.append(k)
                item = QListWidgetItem(f"{k} – {name}")
                self.class_list.addItem(item)
        self.class_list.setCurrentRow(0)

        ## Set up teacher list
        self.all_teachers = []
        self.teacher_list.clear()
        teachers = get_teachers()
        for tid in teachers:
            if tt.tt_data.teacher_ttls.get(tid):
                self.all_teachers.append(tid)
                item = QListWidgetItem(f"{tid} – {teachers.name(tid)}")
                self.teacher_list.addItem(item)
        self.teacher_list.setCurrentRow(0)

#TODO
    @Slot(int)
    def on_class_teacher_currentChanged(self, i):
        pass

    @Slot(int, int, int, int)
    def on_lessons_currentCellChanged(self, r, c, r0, c0):
#TODO--
        print("&&&>>>", r)


    @Slot(int)
    def on_class_list_currentRowChanged(self, row):
        klass = self.all_classes[row]
        self.grid.remove_tiles()
#        self.timetable.show_class(klass)
        self.timetable.enter_class(klass)
#TODO--
        print("§§§ SELECTED CLASS:", klass,
            get_classes()[klass].divisions.divisions
        )

    @Slot(int)
    def on_teacher_list_currentRowChanged(self, row):
        tid = self.all_teachers[row]
        self.grid.remove_tiles()
#        self.timetable.show_teacher(tid)
#TODO
#        self.timetable.enter_teacher(tid)
#TODO--
        print("§§§ SELECTED TEACHER:", tid)

#TODO
    def selected_tile(self, row, col, row0, col0):
        if row >= 0 and row != row0:
            print("§SELECT", row, row0)
#TODO: Will need all the data to enable a search for possible placements:
# Primarily teachers, groups, rooms
# To calculate penalties also other stuff, including placements of all
# other items.
# Should 100% constraints be included with the primaries?

# Can use set_background on the period cell to mark the possible cells.
# Various colours for various degrees of possibility? E.g. absolute no-go
# if a tile in another class must be moved? Only vie direct, conscious
# removal?

class TimetableManager:
    def __init__(self):
        ### Read data from database
        self.tt_data = TimetableData()

    def set_gui(self, gui):
        self.gui = gui

    def enter_class(self, klass):
        grid = self.gui.grid
        self.gui.table_header.setText(get_classes()[klass].name)
        tile_list = self.gui.lessons
        tile_list.clearContents()
        # Sort activities on subject
        tt_lessons = self.tt_data.tt_lessons
        class_activities = sorted(
            (tt_lessons[i] for i in self.tt_data.class_ttls[klass]),
            key=lambda x: x.subject_tag
        )
        tile_list.setRowCount(len(class_activities))
        tiles = []
        tile_list_hidden = []
#TODO--
#        print("\nCLASS", klass)

# Can I share this with the teacher view?
        fixed_time = []
        to_place = []
        unplaced = []
        for row, activity in enumerate(class_activities):
#TODO--
            print("  --", activity)

#TODO: Keep non-fixed times separate from the database? When would they
# be saved, then?

#TODO: What to do with these lists?!
            if activity.time:
                fixed_time.append((activity.time, activity))
                p0 = activity.time
            elif activity.placement0:
                to_place.append((activity.placement0, activity))
                p0 = activity.placement0
            else:
                unplaced.append(activity)
                p0 = 0

#TODO: display data  ... first check placements (fixed first) ...
# ... placements should be done "normally", i.e. with all checks,
# in case the fixed times have changed (or there is an error in the
# database).

# ... Placed and unplaced tiles ...

#TODO: rooms? Shouldn't the rooms per group be available????
# Via the workload entry ... this can, however, be '$', potentially
# leading to multiple rooms.
            x = False
            groups = set()
            tids = set()
            rooms = set()
            sid = activity.subject_tag
            for c in activity.courselist:
                if c.klass == klass:
                    groups.add(c.group)
                    tids.add(c.tid)
                    # The rooms are the acceptable ones!
                    rooms.update(self.tt_data.room_split(c.room))
                else:
                    x = True
#TODO: tool-tip (or whatever) to show parallel courses?
#TODO: The rooms are part of the allocation data and should be checked!
            t_rooms = activity.rooms0 # list of room indexes!
# It could be that not all required rooms have been allocated?
# I would need to compare this with the "roomlists" lists,
# <activity.roomlists>.
#            alloc_rooms = t_rooms.split(',') if t_rooms else []
#            print("???", len(activity.roomlists), rooms, alloc_rooms)

            t_tids = ','.join(sorted(tids)) or '–'
            t_groups, tile_divisions = self.tile_division(klass, groups)
            #t_groups = ','.join(sorted(groups))
            if x:
                t_groups += "+"
#TODO--
#            print("  ...", sid, t_tids, t_groups, t_rooms, tile_divisions)

            tile_list.setItem(row, 0, QTableWidgetItem(sid))
            twi = QTableWidgetItem(str(activity.length))
            twi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_list.setItem(row, 1, twi)
            twi = QTableWidgetItem(t_groups)
            twi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_list.setItem(row, 2, twi)
            tile_list.setItem(row, 3, QTableWidgetItem(t_tids))

# Just testing!!! It should actually be based on existing placement
#            if fixed_time:
#                tile_list.hideRow(row)
#            else:
#                tile_list.showRow(row)

#TODO: The rooms should have been checked by trying to place all
# activities. The atual rooms used would be got from elsewhere!
# The calls to get_rooms are very inefficient ...
            t_rooms_str = ",".join(get_rooms()[r-1][0] for r in t_rooms)
            #print("\n???", t_rooms)
            #print("   ->", t_rooms_str)

            d, p = self.tt_data.period2day_period(p0)
            for i, l, n in tile_divisions:
                tile_index = len(tiles)
                tile = make_tile(
                    grid=grid,
                    tag=tile_index,
                    duration=activity.length,
                    n_parts=l,
                    n_all=n,
                    offset=i,
                    text=sid,
#TODO: Might want to handle the placing of the corners in the configuration?
# Rooms can perhaps only be added when placed, and even then not always ...
                    tl=t_tids,
                    tr=t_groups,
                    br=t_rooms_str,
                )
                tiles.append(tile)
                if d >= 0:
                    grid.place_tile(tile_index, (d, p))
                    tile_list_hidden.append(True)
                else:
                    tile_list_hidden.append(False)

        tile_list.resizeColumnsToContents()


#TODO: Show all activities (class or teacher)
    def show_view(self, activities):
        tile_list = self.gui.lessons
        tile_list.clearContents()
        tile_list.setRowCount(len(activities))
        tiles = []
        tile_list_hidden = []
#TODO--
#        print("\nCLASS", klass)

# Can I share this with the teacher view?
        for row, activity in enumerate(activities):
#TODO--
            print("  --", activity)

            fixed_time = activity.time

#TODO: Keep non-fixed times separate from the database? When would they
# be saved, then?
            if fixed_time:
                d, p = timeslot2index(fixed_time)
#                print("   @", d, p)

            else:
                slot_time = activity.placement0
                if slot_time:
                    d, p = timeslot2index(slot_time)
#                    print("   (@)", d, p)

#TODO: display data

#TODO: rooms? Shouldn't the rooms per group be available????
# Via the workload entry ... this can, however, be '$', potentially
# leading to multiple rooms.

# This bit outside of the function, because it is different for class &
# teacher?
            x = False
#? for teacher ...
            class_groups = set()
            rooms = set()
            sid = activity.subject_tag
            for c in activity.courselist:
                if c.tid == tid:
                    klass = c.klass
                    group = c.group
#                    class_groups.add(???)
                    # The rooms are the acceptable ones!
                    rooms.update(room_split(c.room))
                else:
                    x = True

            tl = sid
            #text = class-group list


#TODO: tool-tip (or whatever) to show parallel courses?
#TODO: The rooms are part of the allocation data and should be checked!
            t_rooms = activity.rooms0 # list of room indexes!
# It could be that not all required rooms have been allocated?
# I would need to compare this with the "roomlists" lists,
# <activity.roomlists>.
#            alloc_rooms = t_rooms.split(',') if t_rooms else []
#            print("???", len(activity.roomlists), rooms, alloc_rooms)

            t_tids = ','.join(sorted(tids)) or '–'
            t_groups, tile_divisions = self.tile_division(klass, groups)
            #t_groups = ','.join(sorted(groups))
            if x:
                t_groups += "+"
#TODO--
#            print("  ...", sid, t_tids, t_groups, t_rooms, tile_divisions)

            tile_list.setItem(row, 0, QTableWidgetItem(sid))
            twi = QTableWidgetItem(str(activity.length))
            twi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_list.setItem(row, 1, twi)
            twi = QTableWidgetItem(t_groups)
            twi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_list.setItem(row, 2, twi)
            tile_list.setItem(row, 3, QTableWidgetItem(t_tids))

# Just testing!!! It should actually be based on existing placement
#            if fixed_time:
#                tile_list.hideRow(row)
#            else:
#                tile_list.showRow(row)

# Perhaps placements should be done "normally", i.e. with all checks,
# in case the fixed times have changed (or there is an error in the
# database).

#TODO: The rooms should have been checked by trying to place all
# activities. The atual rooms used would be got from elsewhere!
# The calls to get_rooms are very inefficient ...
            t_rooms_str = ",".join(get_rooms()[r][0] for r in t_rooms)
            #print("\n???", t_rooms_str)

            for i, l, n in tile_divisions:
                tile_index = len(tiles)
                tile = make_tile(
                    grid=grid,
                    tag=tile_index,
                    duration=activity.length,
                    n_parts=l,
                    n_all=n,
                    offset=i,
                    text=sid,
#TODO: Might want to handle the placing of the corners in the configuration?
# Rooms can perhaps only be added when placed, and even then not always ...
                    tl=t_tids,
                    tr=t_groups,
                    br=t_rooms_str,
                )
                tiles.append(tile)
                if d >= 0:
                    grid.place_tile(tile_index, (d, p))
                    tile_list_hidden.append(True)
                else:
                    tile_list_hidden.append(False)

        tile_list.resizeColumnsToContents()



    def tile_division(self, klass, groups):
        # Gather division components
        div2pgroups, g2div = self.tt_data.group_division[klass]
        divi = -1
        for g in groups:
            i, dgs = g2div[g]
            if i < 0:
                # Any other groups are irrelevant if the whole class is
                # included
                return (WHOLE_CLASS, [(0, 1, 1)])
            if divi != i:
                if divi >= 0:
                    # Groups from multiple divisions, assume whole class
                    return (WHOLE_CLASS, [(0, 1, 1)])
                else:
                    divi = i
                    dgset = set(dgs)
            else:
                dgset.update(dgs)
        # Construct tile divisions
        div_groups = div2pgroups[divi]
        n = len(div_groups)
        if len(dgset) == n:
            return (WHOLE_CLASS, [(0, 1, 1)])
        l = 0
        i = 0
        tiles = []
        for g in div_groups:
            if g in dgset:
                if l == 0:
                    p = i
                    l = 1
                else:
                    l += 1
            elif l:
                tiles.append((p, l, n))
                l = 0
            i += 1
        if l:
            tiles.append((p, l, n))
        return (','.join(sorted(groups)), tiles)


def make_tile(
    grid,
    tag,
    duration,
    n_parts,
    n_all,
    offset,
    text,
    tl=None,
    tr=None,
    br=None,
    bl=None
):
    tile = grid.new_tile(
        tag,
        duration=duration,
        nmsg=n_parts,
        offset=offset,
        total=n_all,
        text=text
    )
    if tl:
        tile.set_corner(0, tl)
    if tr:
        tile.set_corner(1, tr)
    if br:
        tile.set_corner(2, br)
    if bl:
        tile.set_corner(3, bl)
    return tile


class WeekGrid(GridPeriodsDays):
    def __init__(self, breaks):
        super().__init__(
            get_days().key_list(),
            get_periods().key_list(),
            breaks
        )

    def make_context_menu(self):
        self.context_menu = QMenu()
#TODO:
        Action = self.context_menu.addAction("Seek possible placements")
        Action.triggered.connect(self.seek_slots)

    def seek_slots(self):
        print("seek_slots:", self.context_tag)
        #tile = self.tiles[self.context_tag]


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from core.db_access import open_database
    from ui.ui_base import run
    _db = get_database()

    widget = TimetableEditor()
    widget.enter()

    widget.resize(1000, 550)
    run(widget)
