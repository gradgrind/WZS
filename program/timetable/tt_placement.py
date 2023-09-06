"""
timetable/tt_placement.py

Last updated:  2023-09-05

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
    teacher_weeks: list[list[int]]
    group_weeks: list[list[int]]
    room_weeks: list[list[int]]


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
    integers: The timeslot (0 for unallocated) followed by the rooms
    where there is a choice – the "fixed" rooms are not included.
    A room value is 0 when it is not yet allocated (otherwise 1+).
    """
    state = [[0]] # First entry is null (not a lesson)
    for ttl in tt_lessons:
        if ttl:
            lstate = [0]
            state.append(lstate)
            for rc in ttl.room_choices:
                lstate.append(0)
    return state

#NOTE: As the compulsory single rooms of an activity must be available
# for a placement to be successful, there is no need to have them as
# part of the "state". Of course, also a deallocation will have to
# seek rooms in two places, the "fixed" ones and the "chosen" ones.


def very_hard_constraints(allocation, tt_lesson, timeslot):
    """Test whether the lesson/activity can be placed in the specified
    slot.
    The teachers, class-groups and compulsory single rooms are tested.
    Let's call these "very hard constraints". It can be seen as a first
    stage, which will filter out many non-fitting placement attempts
    quite quickly.
    Room requirements where there is a choice are handled separately,
    as that is quite a bit more complicated. That is postponed to the
    evaluation of other hard constraints.

    allocation: placement data structures
    tt_lessons: the activity vector
    ttli: index of the activity to test (1+)
    timeslot: index of the time slot to test (1+)

    Return a set of blocking activity indexes, empty if the allocation
    is possible in the given time-slot.
    """
    length = tt_lesson.length
    blockers = set()
    #print("TIMESLOT", timeslot, allocation.teacher_weeks[timeslot])
    #print("TIMESLOT", 1, allocation.teacher_weeks[1])
    while length > 0:
        # Test teachers
        pslot = allocation.teacher_weeks[timeslot]
        for t in tt_lesson.teachers:
            i = pslot[t]
            if i != 0:
                print("TEACHER", t, i, timeslot)
                blockers.add(i)
        # Test class-groups
        pslot = allocation.group_weeks[timeslot]
        for cg in tt_lesson.classgroups:
            i = pslot[cg]
            if i != 0:
                print("GROUP", cg, i, timeslot)
                blockers.add(i)
        # Test single compulsory rooms
        pslot = allocation.room_weeks[timeslot]
        for r in tt_lesson.fixed_rooms:
            i = pslot[r]
            if i != 0:
                print("ROOM", r, i, timeslot)
                blockers.add(i)
        # Room choices are ignored here
        length -= 1
        timeslot += 1
    return blockers


def hard_constraints():
    print("TODO")
# Apart from going through the various hard constraints relevant to a
# lesson placement, a list of rooms for the choice list should be
# produced, which then needs to be available for the actual placement.
# If multiple activities with room choices are to be placed in a time-
# slot, a more intricate algorithm would be needed to sort out the
# compatibility ...
# If an attempt is made to place an activity in a slot and it doesn't
# work because of rooms occupied by choices of other activities, it
# MIGHT be reasonable to attempt a reallocation of the choice rooms,
# but is that really what is wanted? Quite possibly, but perhaps I
# should first try the placement without reorganizing the rooms.
# Unfortunately, an automatic reallocation of rooms across activities
# might well turn out to be a touch more complex than I would like
# (especially when considering varying activity lengths).



def resolve_room_choice(
    allocation: ALLOCATION,
    tt_lesson: TT_LESSON,
    timeslot: int,
):
    """Try to allocate rooms satisfying the choice lists.
    """
    # Handle possibility of length > 1
    rslots = [
        allocation.room_weeks[i]
        for i in range(timeslot, timeslot + tt_lesson.length)
    ]
#TODO: Should I allocate the rooms which are possible even if others
# are not possible? If the rooms are a soft constraint that would
# probably be sensible.

    # Reduce the lists to contain only available rooms
    rclists = []
    for rc in tt_lesson.room_choices:
        l = []
        rclists.append(l)
        for r in rc:
            for rs in rslots:
                if rs[r] != 0:  # room in use
                    break
            else:
                l.append(r)
#TODO: Don't do this if I want partial allocation when some rooms
# don't work:
        if not l:
            return None
    # Initialize result list
    rooms = [0] * len(choice_lists)
    # Recursive function to build room list using first possible
    # room combination
    def resolve(i, blocked):
        try:
            choices = rclists[i]
        except IndexError:
            return True
        for r in choices:
            # Check that the room is free
            if r not in blocked:
                # Try to fill the remaining positions
                if resolve(i + 1, blocked + {r}):
                    rooms[i] = r
                    return True
        return False
#TODO: If returning also partial room lists, I would be faced with the
# difficulty of deciding which imperfect allocation to return ...
    if resolve(0, set()):
        return rooms
    return None


def seek_rooms(rlists):
#def seek_rooms():
#TODO: reduced room lists taking already allocated rooms into account
    minzeros = 0
    for rl in rlists:
        if not rl:
            minzeros += 1

    bestzeros = len(rlists)
    best = [0] * bestzeros
    maxi = bestzeros - 1
    zeros = 0
    i = 0
    used = []
    filtered_lists = []
    while i >= 0:
        if i == maxi:
            ## Done?
            # Get the first free room
            for r in rlists[i]:
                if r not in used:
                    if zeros == minzeros:
                        # An optimal solution has been found
                        used.append(r)
                        return used
                    if zeros < bestzeros:
                        best = used.copy()
                        best.append(r)
                        bestzeros = zeros
                    break
            else:
                # No free room
                if zeros + 1 == minzeros:
                    # An optimal solution has been found
                    used.append(0)
                    return used
                if zeros + 1 < bestzeros:
                    best = used.copy()
                    best.append(0)
                    bestzeros = zeros + 1
            i -= 1
        elif i < len(filtered_lists):
            rl = filtered_lists[i]
            if rl:
                # Try next room
                used[i] = rl.pop()
                i += 1
            else:
                # No more rooms to try
                if used.pop() == 0:
                    zeros -= 1
                del filtered_lists[i]
                i -= 1
        else:
            # Build reversed filtered list (for popping rooms)
            rl0 = rlists[i]
            rl = []
            x = len(rl0)
            while x > 0:
                x -= 1
                r = rl0[x]
                if r not in used:
                    rl.append(r)
            filtered_lists.append(rl)
            if rl:
                used.append(rl.pop())
            else:
                # No free room at this level
                used.append(0)
                zeros += 1
            i += 1
    return best


"""rl0 = [
    [1, 2],
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    [1, 2],
    [2, 3, 4, 5, 6, 7, 8, 9],
    [1, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
]
import timeit
rlists = rl0
nnn = 10000
print(timeit.timeit(seek_rooms, number=nnn, globals=globals()))
print("$$$$", seek_rooms())
"""

#########################################################

def test_placement(
    allocation: ALLOCATION,
    tt_lesson: TT_LESSON,
    timeslot: int,
    saved_rooms: Optional[list[int]]
) -> bool:
    """Check all hard contraints for the given placement.
    """
    if very_hard_constraints(allocation, tt_lesson, timeslot):
        return False

#TODO: Is this at all appropriate here? Isn't it rather a question of
# whether a placement is at all possible. If the saved rooms fit, this
# should be done when actually doing the placement. If they don't fit,
# then others will be used.
    # Check the saved rooms, if supplied
    if saved_rooms and not test_room_allocation(
        allocation,
        tt_lesson.room_choices,
        saved_rooms,
        timeslot,
        tt_lesson.length
    ):
        return False

    return not hard_constraints(allocation, tt_lesson, timeslot)


def place_with_room_choices(
    allocation: ALLOCATION,
    tt_lessons: list[Optional[TT_LESSON]],  # only the first entry is <None>
    ttli: int,
    timeslot: int,
    state_vector: list[list[int]],
    saved_rooms: Optional[list[int]]
):
    """The activity is to be placed in the given time-slot.
    If a list of saved rooms is provided, try to use these.
    It is assumed that the possibility of the placement has been
    checked already!
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
#TODO: comments not clear!
    # Place single compulsory rooms
    pslot = allocation.room_weeks[timeslot]
    # Skip the compulsory single rooms (see comment to <get_state_vector()>)
    for r in ttl.fixed_rooms:
        pslot[r] = ttli

    # Room choices ...
    if saved_rooms and test_room_allocation(
        allocation,
        ttl.room_choices,
        saved_rooms,
        timeslot,
        ttl.length
    ):
        pass


    # Deal with no saved rooms


    for rc in ttl.room_choices:
        i += 1
        state[i] = 0
    #print("[]", timeslot, allocation.teacher_weeks)


def place_lesson_initial(
    allocation: ALLOCATION,
    tt_lessons: list[Optional[TT_LESSON]],  # only the first entry is <None>
    ttli: int,
    timeslot: int,
    state_vector: list[list[int]],
):
    """Place the given activity in the specified time slot.
    !!! Only do this when the allocation slots are really empty, that is
    not checked here.

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
#TODO: comments not clear!
    # Place single compulsory rooms
    pslot = allocation.room_weeks[timeslot]
    # Skip the compulsory single rooms (see comment to <get_state_vector()>)
    for r in ttl.fixed_rooms:
        pslot[r] = ttli
    # Room choices are not allocated here
    for rc in ttl.room_choices:
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
#



#TODO
def full_placement(tt_data, tt_lessons, saved_state=None):
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
        timeslot = ttl.time
        if timeslot != 0:
#TODO: Could have been "^ ..." (lesson reference)!
            blockers = very_hard_constraints(allocation, tt_lessons[i], timeslot)
            if blockers:
                #print("   BLOCKERS", i, blockers)
                ttlx = tt_lessons[list(blockers)[0]]
                REPORT(
                    "ERROR",
                    T["CLASHING_FIXED_TIME"].format(
                        activity1=print_activity(ttlx),
                        activity2=print_activity(ttl),
                        time=timeslot_text(timeslot)
                    )
                )
                continue
        elif saved_state:
            timeslot = saved_state[i][0]
            if timeslot == 0:
                continue
            blockers = very_hard_constraints(allocation, tt_lessons[i], timeslot)
#--
#            print("?????", i, timeslot, blockers)

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


# Do I want to keep this structure?
def get_saved_state(tt_lessons):
    """Extract the placements from the LESSONS table (via the activities
    list).
    """
    state = [None]
    for ttli in range(1, len(tt_lessons)):
        ttl = tt_lessons[ttli]
        time = ttl.placement0
        if time > 0:
            rooms = ttl.rooms0
            # The rooms might not correspond (even in number) to those
            # expected ...
            state.append([time] + ttl.rooms0)
        else:
            state.append([0])
    return state


# See init_timeslot_text below
def timeslot_text(timeslot):
    days = get_days()
    periods = get_periods()
    if timeslot == 0:
        return ""
    #print("§DAYS:", days)
    #print("§PERIODS:", periods)
    d, p = divmod(timeslot - 1, len(periods))
    return f"{days[d][0]}.{periods[p][0]}"


# The returned function is a bit more efficient than the above for repeated use.
def init_timeslot_text():
    def tt(timeslot):
        if timeslot == 0:
            return ""
        d, p = divmod(timeslot - 1, nperiods)
        return f"{days[d]}.{periods[p]}"
    days = [x[0] for x in get_days()]
    periods = [x[0] for x in get_periods()]
    nperiods = len(periods)
    return tt


def test_room_allocation(
    allocation: ALLOCATION,
    requirements: list[list[int]],
    test_rooms: list[int],
    timeslot: int,
    length: int
):
    """Check the availability of the saved room list – supplied as
    <test_rooms> – and try to correlate it with the room requirements
    (choices) list.
    Return true if successful (the rooms can be used).
    """
    # There must be the same number of entries in both lists
    if len(requirements) != len(test_rooms):
        return False
    # Check availability of requested rooms
    while length > 0:
        pslot = allocation.room_weeks[timeslot]
        for r in test_rooms:
            if pslot[r] != 0:
                return False
        timeslot += 1
        length -= 1
    # Attempt to correlate requested rooms with required rooms
    def select(rs, ri):
        # A recursive function
        try:
            rs.intersection(requirements[ri])
        except IndexError:
            return True # all requirements tested
        for r in intersects.pop():
            if select(rs - {r}, ri + 1):
                return True
        return False
    return select(set(test_rooms), 0)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from core.db_access import open_database
    open_database()

    """
    from random import randrange
    from timeit import default_timer as timer
    from datetime import timedelta
    start = timer()
    for i in range(1000000):
        t = timeslot_text(randrange(46))
    end = timer()
    print(timedelta(seconds=end-start))
    timeslot_text2 = init_timeslot_text()
    start = timer()
    for i in range(1000000):
        t = timeslot_text2(randrange(46))
    end = timer()
    print(timedelta(seconds=end-start))
    quit(1)
    """

    """
    timeslot_text2 = init_timeslot_text()
    print("§", timeslot_text2(0))
    print("§", timeslot_text2(10))
    print("§", timeslot_text2(11))
    quit(1)
    """

    from timetable.tt_basic_data import read_tt_db
    tt_data, tt_lists = read_tt_db()
    tt_lessons, class_ttls, teacher_ttls = tt_lists

    saved_state = get_saved_state(tt_lessons)
    full_placement(tt_data, tt_lessons, saved_state)

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
