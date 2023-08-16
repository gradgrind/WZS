#TODO ...
"""
timetable/tt_placement.py

Last updated:  2023-08-16

Handle the basic information for timetable display and processing.


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
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import start
    start.setup(os.path.join(basedir, 'TESTDATA'))

#T = TRANSLATIONS("timetable.tt_placement")

### +++++

from typing import NamedTuple

from core.basic_data import get_days, get_periods

### -----


class PlacementEngine:
    def __init__(self):

        return

# Index 0 in TT_LESSONS is reserved for null/"empty", it is not a TT_LESSON.
# I would need allocations for each tt_lesson (time + rooms). The rooms
# would ideally be correlatable with the room requirements. There could also
# be entries for unallocated room requirements?

class ALLOCATION(NamedTuple):
    teacher_weeks: list[int]
    group_weeks: list[int]
    room_weeks: list[int]


def data_structures(n_teachers, n_groups, n_rooms):
#?
    # First cell (index 0) of week vector is not used.
    n_week_cells = len(get_days()) * len(get_periods()) + 1
    week_placements = [0] * n_week_cells

    return ALLOCATION(
        [week_placements] * n_teachers,       # incl. null teacher
        [week_placements] * n_groups,         # incl. null class
        [week_placements] * n_rooms           # incl. null room
    )

# I also need a simple representation of the allocation state (time and
# rooms) of each tt_lesson. The data structure should be appropriate for
# storing a complete allocation state, which can be used to restore a
# previous state. A list (one entry per tt_lesson) of lists (e.g.
# [time, room, room, ... ]) would be a possibility. To preserve this
# over runs, the tt_lessons should be converted to lesson-ids and the
# times and rooms converted to their text forms.
# Would it make sense to save this data separately from the LESSONS
# table? Perhaps if multiple results with the same configuration are
# to be saved? But saving the whole database is also a serious contender
# for this scenario.
def get_state_vector(tt_lessons):
    """Return an empty state vector.
    """
    state = [0] # First entry is null (not a lesson)
    for ttl in tt_lessons:
        if ttl:
            lstate = [0]
            state.append(lstate)
            rl3 = ttl.roomlists
            for i in range(len(rl3[0]) + len(rl3[1]) + len(rl3[2])):
                lstate.append(0)
    return state


def can_place_lesson(allocation, tt_lessons, ttli, timeslot):
    """Test whether the lesson can be placed in the specified slot.
#?
    It returns diagnostics – blocking teachers, groups and rooms as
    well as the tt_lesson indexes.
    Only a set of basic constraints is checked here.
    """
    # Need the teachers, groups and rooms
#TODO: Need a redesigned TT_LESSON with teacher indexes, ... !
    ttl = tt_lessons[ttli]
    blockers = set()
#    tblockers = set()
#    cgblockers = set()
    for t in ttl.teachers:
        i = allocation.teacher_weeks[t][timeslot]
        if i != 0:
#            tblockers.add(t)
            blockers.add(i)
    for cg in ttl.classgroups:
        i = allocation.group_weeks[cg][timeslot]
        if i != 0:
#            cgblockers.add(cg)
            blockers.add(i)
#TODO ...
# The atomic groups are probably not so helpful as diagnostics ...
# Would it be enough to register just the blocking lessons?
# I could just indicate whether it was teacher, group or room, without
# trying to go into the details?
    rl = ttl.roomlists
    for r in rl[0]:
        i = allocation.room_weeks[r][timeslot]
        if i != 0:
            blockers.add(i)
    for rln in rl[1]:
        for r in rln:
            i = allocation.room_weeks[r][timeslot]
            if i == 0:
                break   # room possible
        else:
            blockers.add(i)
    return blockers


def full_placement(tt_data, tt_lessons):
    day2index = get_days().index
    periods = get_periods()
    nperiods = len(periods)
    period2index = periods.index
    allocation = data_structures(
        len(tt_data.teacher_index),
        tt_data.n_class_group_atoms + 1,
        len(tt_data.room_index),
    )
    tt_state = get_state_vector(tt_lessons)
    i = 0
    imax = len(tt_lessons) - 1
    while i < imax:
        i += 1
        ttl = tt_lessons[i]

        timeslot_txt = ttl.placement0
        if timeslot_txt:
#TODO: Could be "^ ..." (lesson reference)!
            d, p = timeslot_txt.split(".")
            timeslot = day2index(d) * nperiods + period2index(p) + 1
#TODO: convert to week slot index
        print("???", i, timeslot, can_place_lesson(allocation, tt_lessons, i, timeslot))
# if no blockers, do the placement, otherwise add to unallocated list/map
# when all done (?) calculate penalties?
# Penalties are probably only relevant when all tt_lessons have been
# placed ...

# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from core.db_access import open_database
    open_database()

    from timetable.tt_basic_data import read_tt_db
    tt_data, tt_lists = read_tt_db()
    tt_lessons, class_ttls, teacher_ttls = tt_lists

    full_placement(tt_data, tt_lessons)

    quit(0)

    print(f"ROOMS ({len(tt_data.room_index) - 1}):", tt_data.room_index)

    allocation = data_structures(
        len(tt_data.teacher_index),
        tt_data.n_class_group_atoms + 1,
        len(tt_data.room_index),
    )

    print("\n tt_lessons:")
    tt_state = get_state_vector(tt_lessons)
    for tts in tt_state:
        print("  --", tts)
