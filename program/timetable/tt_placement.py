#TODO ...
"""
timetable/tt_placement.py

Last updated:  2023-08-21

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

T = TRANSLATIONS("timetable.tt_placement")

### +++++

from typing import NamedTuple, Optional

from core.basic_data import get_days, get_periods
from timetable.tt_basic_data import TT_LESSON

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
    """Return an empty data structure to contain teacher, group and
    room placements. There is a cell for each time slot, which can
    contain the index of an activity (0 for empty).
    The primary division of each table is the time slot because most
    allocating and testing will be done with regard to a single time slot.
    All "real" indexes start at 1, 0 being used as "null".
    """
    n_week_cells = len(get_days()) * len(get_periods()) + 1
    return ALLOCATION(
        [[0] * n_teachers for i in range(n_week_cells)],
        [[0] * n_groups for i in range(n_week_cells)],
        [[0] * n_rooms for i in range(n_week_cells)],
    )

# I also need a simple representation of the allocation state (time and
# rooms) of each tt_lesson. The data structure should be appropriate for
# storing a complete allocation state, which can be used to restore a
# previous state. A list (one entry per tt_lesson) of lists (e.g.
# [time, room, room, ... ]) would be a possibility. To preserve this
# over runs, the tt_lessons should be converted to lesson-ids and the
# times and rooms converted to their text forms. Unallocated rooms
# would not need to appear in the persistent version.
# Would it make sense to save this data separately from the LESSONS
# table? Perhaps if multiple results with the same configuration are
# to be saved? But saving the whole database is also a serious contender
# for this scenario.
def get_state_vector(tt_lessons):
    """Return an empty state vector.
    This contains an entry for each activity. Each entry is a list of
    integers: The timeslot (0 for unallocated) followed by the rooms,
    the latter corresponding to the list of room requirements (1+ for an
    allocated room, 0 for an unallocated one).
    """
    state = [0] # First entry is null (not a lesson)
    for ttl in tt_lessons:
        if ttl:
            lstate = [0]
            state.append(lstate)
            rl3 = ttl.roomlists
#TODO: Actually the third entry in <rl3> is deprecated, but may still
# appear for a while ...
            for i in range(len(rl3[0]) + len(rl3[1]) + len(rl3[2])):
                lstate.append(0)
    return state

#TODO: As the compulsory single rooms of an activity must be avaiable
# for a placement to be successful, there is actually no need to have
# them as part of the "state". Of course, also a deallocation would
# then have to seek rooms in two places.


def can_place_lesson(allocation, tt_lessons, ttli, timeslot):
    """Test whether the lesson/activity can be placed in the specified
    slot.
    The teachers, class-groups and compulsory single rooms are tested.
    Room requirements where there is a choice are not considered here,
    as that is quite a bit more complicated. That is postponed to the
    evaluation of penalties, which is only done when all activities
    have been placed according to this simple test.

    allocation: placement data structures
    tt_lessons: the activity vector
    ttli: index of the activity to test (1+)
    timeslot: index of the time slot to test (1+)

    Return a set of blocking activity indexes.
    """
    ttl = tt_lessons[ttli]
    length = ttl.length
    blockers = set()
    #print("TIMESLOT", timeslot, allocation.teacher_weeks[timeslot])
    #print("TIMESLOT", 1, allocation.teacher_weeks[1])
    while length > 0:
        # Test teachers
        pslot = allocation.teacher_weeks[timeslot]
        for t in ttl.teachers:
            i = pslot[t]
            if i != 0:
                print("TEACHER", t, i, ttl.time)
                blockers.add(i)
        # Test class-groups
        pslot = allocation.group_weeks[timeslot]
        for cg in ttl.classgroups:
            i = pslot[cg]
            if i != 0:
                print("GROUP", cg, i, ttl.time)
                blockers.add(i)
        # Test single compulsory rooms
        pslot = allocation.room_weeks[timeslot]
        rl = ttl.roomlists
        for r in rl[0]:
            i = pslot[r]
            if i != 0:
                print("ROOM", r, i, ttl.time)
                blockers.add(i)
        # Room choices are ignored here
        length -= 1
        timeslot += 1
    return blockers


def place_lesson_initial(
    allocation: ALLOCATION,
    tt_lessons: list[Optional[TT_LESSON]],  # only the first entry is <None>
    ttli: int,
    timeslot: int,
    state_vector: list[list[int]],
):
    """Place the given activity in the specified time slot.
    !!! Only do this when the allocation slots are really empty.

    allocation: placement data structures
    tt_lessons: the activity vector
    ttli: index of the activity to test (1+)
    timeslot: index of the time slot to test (1+)
    state_vector: current placements of all activities (time, rooms)
    """
    ttl = tt_lessons[ttli]
    #print("\n??? TTL:", ttli, timeslot)
    #print("[]", len(allocation.teacher_weeks), allocation.teacher_weeks)
    length = ttl.length
    state = state_vector[ttli]
    state[0] = timeslot

#TODO: deal with length (number of periods)
    i = 0
    # Place teachers
    pslot = allocation.teacher_weeks[timeslot]
    for t in ttl.teachers:
        pslot[t] = ttli
    # Place class-groups
    pslot = allocation.group_weeks[timeslot]
    for cg in ttl.classgroups:
        pslot[cg] = ttli
    # Place single compulsory rooms
    pslot = allocation.room_weeks[timeslot]
    rl = ttl.roomlists
    for r in rl[0]:
        pslot[r] = ttli
        i += 1
        state[i] = r
    # Room choices are not allocated here
    for rc in rl[1]:
        i += 1
        state[i] = 0
#TODO: Actually the third entry in <rl> is deprecated, but may still
# appear for a while ...
    for rc in rl[2]:
        i += 1
        state[i] = 0
    #print("[]", timeslot, allocation.teacher_weeks)


# This should place all the activities/lessons in the timetable which
# are in the supplied placement list – times and rooms. If a time
# or a compulsory single room doesn't work, the activity is left
# unallocated. The room choices are only handled if all activities have
# been successfully placed – this is because it is part of the weighting
# system. The basic idea is that the primary placement should be simple
# and fast, allowing many impossible placements to be filtered out
# quickly. The handling of weighted constraints is inevitably more
# complex and some constraints only make sense when all activities have
# been placed. There is not much point in calculating weights/penalties
# for incomplete timetables.
#TODO
def full_placement(tt_data, tt_lessons, saved_state=None):
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
        timeslot_txt = ttl.time
        if timeslot_txt:
#TODO: Could be "^ ..." (lesson reference)!
            d, p = timeslot_txt.split(".")
            timeslot = day2index(d) * nperiods + period2index(p) + 1
            blockers = can_place_lesson(allocation, tt_lessons, i, timeslot)
            if blockers:
                #print("   BLOCKERS", i, blockers)
                ttlx = tt_lessons[list(blockers)[0]]
                REPORT(
                    "ERROR",
                    T["CLASHING_FIXED_TIME"].format(
                        activity1=print_activity(ttlx),
                        activity2=print_activity(ttl),
                        time=timeslot_txt
                    )
                )
                continue
        elif saved_state:
            timeslot = saved_state[i]
            if timeslot == 0:
                continue
            blockers = can_place_lesson(allocation, tt_lessons, i, timeslot)
            #print("?????", i, timeslot, blockers)
            if blockers:
                continue
        else:
            continue

# if no blockers, do the placement, otherwise add to unallocated list/map
# when all done (?) calculate penalties?
# Penalties are probably only relevant when all tt_lessons have been
# placed ...
        place_lesson_initial(allocation, tt_lessons, i, timeslot, tt_state)

    #for data in tt_state:
    #    print(" --", data)


def print_activity(tlesson):
    course1 = tlesson.courselist[0]
    multi = " ..." if len(tlesson.courselist) > 1 else ""
    g = f"{course1.klass}.{course1.group}"
    return f"{g}|{course1.tid}{multi} :: {tlesson.subject_tag}"


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
