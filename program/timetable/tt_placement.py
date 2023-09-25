"""
timetable/tt_placement.py

Last updated:  2023-09-25

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

#TODO: What should these be?! As they are collected in a set they must
# be hashable.
DAY_OVERFLOW = "Day overflow"
TEACHER_BLOCKED = "Teacher(s) unavailable"
GROUP_BLOCKED = "Group(s) unavailable"
ROOM_BLOCKED = "Room(s) unavailable"

### -----

#?
class PlacementEngine:
    def __init__(self):

        return

# Index 0 in TT_LESSONS is reserved for null/"empty", it is not a
# TT_LESSON.
# I would need allocations for each tt_lesson (time + rooms). The rooms
# would ideally be correlatable with the room requirements, but this
# might not be very feasible. There could also be entries for
# unallocated room requirements?


class Allocation:
    __slots__ = (
        "tt_data", #: TimetableData
        "teacher_weeks", #: list[list[int]]
        "group_weeks", #: list[list[int]]
        "room_weeks", #: list[list[int]]
        "allocation_state", #: list[list[int, list[int]]]
    )

    def __init__(self, tt_data):
        """Set up an empty data structure for the collection of lesson
        placements for the timetable.
        Teacher, group and room placements are stored in arrays of cells,
        one for each time slot, each containing the index of an actiity
        (0 for empty). The primary division of each of these arrays is
        the time slot because most allocating and testing will be done
        with regard to a single time slot.
        In addition there is an array with entries for each lesson
        (activity). This contains, for each lesson, a pair of values,
        firstly the time slot – 0 for unallocated – and secondly a list
        of chosen room indexes (not the "fixed" ones) – again 0 for
        unallocated / no room selected.
        All "real" indexes start at 1, 0 generaaly being used as a "null".
        """
        self.tt_data = tt_data
        n_week_cells = tt_data.days_per_week * tt_data.periods_per_day + 1
        n_teachers = len(tt_data.teacher_index)
        self.teacher_weeks = [[0] * n_teachers for i in range(n_week_cells)]
        n_groups = tt_data.n_class_group_atoms + 1
        self.group_weeks = [[0] * n_groups for i in range(n_week_cells)]
        n_rooms = len(tt_data.room_index)
        self.room_weeks = [[0] * n_rooms for i in range(n_week_cells)]
        # Now the lesson allocation space
        state = [[0, []]]
        for ttl in tt_data.tt_lessons[1:]:
            state.append([0, [0] * len(ttl.room_choices)])
        self.allocation_state = state

# To preserve the allocation state over runs, the tt_lesson indexes
# should be converted to lesson-ids and the times and rooms converted
# to their text forms. Unallocated rooms would not need to appear in the
# persistent version.
# Would it make sense to save this data separately from the LESSONS
# table? Perhaps if multiple results with the same configuration are
# to be saved? But saving the whole database is also a serious contender
# for this scenario.
#NOTE: As the compulsory single rooms of an activity must be available
# for a placement to be successful, there is no need to have them as
# part of the "state". Of course, also a deallocation will have to
# seek rooms in two places, the "fixed" ones and the "chosen" ones.


def critical_constraints(
    allocation: Allocation,
    tt_lesson: TT_LESSON,
    timeslot: int
):
    """Test whether the lesson/activity can be placed in the specified
    slot.
    The teachers, class-groups and compulsory single rooms are tested.
    Let's call these "critical constraints", where a breach would be
    physically impossible. It should filter out many non-fitting
    placement attempts quite quickly.

    Room requirements where there is a choice are handled separately,
    as that is quite a bit more complicated. That is regarded as a
    "somewhat" soft constraint.

    Parameters:
        allocation: placement data structures
        tt_lesson: the lesson / activity
        timeslot: index of the time slot to test (1+)

    Return blocking information:
        {lesson-id: [cause, ...]}

    The result will be empty if the allocation is possible in the given
    time-slot. Where the cause of blockage is not another lesson, the
    lesson-id field will be -1.
    """
#TODO: Using a dict may be okay for manual placement, but for automatic
# placement, this function should be replaced by one which returns, say,
# false as soon as it detects a problem.
    blockers = {}   # {lesson-id: [cause, ...]}
    #print("TIMESLOT", timeslot, allocation.teacher_weeks[timeslot])
    #print("TIMESLOT", timeslot, allocation.group_weeks[timeslot])

    # Check that the start time is not too late to fit in the day
    nperiods = allocation.tt_data.periods_per_day
    if (timeslot - 1) % nperiods + tt_lesson.length > nperiods:
#TODO--
        print("!!! DAY overflow:", timeslot, tt_lesson.length, tt_lesson.lesson_id)

        blockers[-1] = {DAY_OVERFLOW}
        return blockers

    t = timeslot
    tmax = t + tt_lesson.length
    while t < tmax:
        # Test teachers
        pslot = allocation.teacher_weeks[t]
        for tx in tt_lesson.teachers:
            i = pslot[tx]
            if i != 0:
#TODO--
                print("TEACHER", tx, i, t)

                try:
                    blockers[i].add(TEACHER_BLOCKED)
                except KeyError:
                    blockers[i] = {TEACHER_BLOCKED}
        # Test class-groups
        pslot = allocation.group_weeks[t]
        for cg in tt_lesson.classgroups:
            i = pslot[cg]
            if i != 0:
#TODO--
                print("GROUP", cg, i, t)

                try:
                    blockers[i].add(GROUP_BLOCKED)
                except KeyError:
                    blockers[i] = {GROUP_BLOCKED}

#TODO:  if allocation.rooms_weighting == "":
# ... otherwise room allocation is regarded as a soft constraint
        # Test single compulsory rooms
        pslot = allocation.room_weeks[t]
        for r in tt_lesson.fixed_rooms:
            i = pslot[r]
            if i != 0:
#TODO--
                print("ROOM", r, i, t)

                try:
                    blockers[i].add(GROUP_BLOCKED)
                except KeyError:
                    blockers[i] = {GROUP_BLOCKED}

        # Room choices are ignored here

        t += 1
    return blockers


#TODO: As far as constraint handling is concerned, it looks like it
# might be best to handle all non-critical constraints together. Hard
# constraints could be placed at the head of the processing queue. They
# can be given very large penalties in manual mode; in automatic mode
# they could cause processing of the queue to be aborted.
# Room choices may be only available as soft constraints, but perhaps
# with a high penalty? Alternatively there could be a configuration
# value to determine the hardness of room requirements – perhaps with
# distinct values for fixed rooms and room choice lists.
def test_constraints(
    allocation: Allocation,
    tt_lesson: TT_LESSON,
    timeslot: int,
    undo: bool
):
    """Test non-critical constraints for the placement of an activity.
    Some of the tests require that the activity is actually placed, so
    if this is only a test, the activity must be removed afterwards.
    The parameter <undo> acts as a switch for the removal (a true value
    will cause the activity to be removed again).
    """
    print("TODO")

# In general, the evaluation of penalties should perhaps be ordered
# according to the weightings. It might be possible to speed up some
# uses of the function by, for example, stopping when the first
# constraint fails – if the exact penalty is not critical. For testing
# placement possibilities – where perhaps many slots or lessons must
# be tested – a very rough estimate of the penalty might be enough.
# Especially for very high priority constraints ("+") this could be
# enough.

# A further optimisation would be to check only constraints which might
# have been affected by a move. The constraints would then need to be
# associated with activities, classes and teachers. That could make
# the priority-sorting tricky.

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

#TODO: Only for manual placement? ...
# But it's not a blocking constraint anyway!
#    zeros, room_choice = resolve_room_choice(
#        allocation,
#        tt_lesson,
#        timeslot
#    )
#    if zeros > 0:
#        # Don't need to test other constraints
#        return None

#TODO: Would I want to know which rooms / lessons were blocking the allocation?

    changes = allocate_lesson()
    hc_blocked = test_hard_constraints()

    if undo or hc_blocked:
        undo_changes(changes)

#TODO: test other constraints.
# Which constraints should be tested here?
# 1) not some gaps – these are relevant only when all placements have been done
# 2) not some minimum constraints – see 1.
# 3) maximum constraints:
#     - lessons per day (teacher or class/group)
#     - lessons without break (teacher or class/group?)
# 4) min-days-between-activities
# 5) not-after (direct or any time?)
# 6) not-on-same-day (combine with min-days-between-activities?)
# 7) lunch break

# Basically, I would just need to evaluate all (relevant?) constraints.
# Something like:
    #for c in constraints:
    #    p = c.evaluate()
    #    #? if p < 0: ... break
    #    penalty += p
# Of course, if I want to know the penalty due to placing a particular
# activity, I would need to restrict the evaluation to the constraints
# whose value changes. Or else see how the total changes ... (does the
# existence of hard constraints, or special high-penalty constraints
# affect this?)

    return hc_blocked #? include room choices?

# It should be possible to detect blocking lessons automatically so that
# the placement of a particular lesson can be forced. Perhaps not the
# room choices, though?


def resolve_room_choice(
    allocation: Allocation,
    tt_lesson: TT_LESSON,
    timeslot: int,
):
    """Try to allocate rooms satisfying the choice lists.
    If a full room list is not possible with the available rooms,
    the returned list will contain one or more null (0) rooms.
    """
#TODO: Perhaps I don't need to return the number of zeros – it depends
# on how the results are used. It could be that the result is always
# used, in which case the zeros could be counted. Are the rooms
# directly allocated?
    # Handle possibility of length > 1
    rslots = [
        allocation.room_weeks[i]
        for i in range(timeslot, timeslot + tt_lesson.length)
    ]

    # Check availability of rooms, noting blocking lessons?
    # Maybe the blocking lessons are only needed when manually choosing
    # a room. For the penalty calculation, only the fact of the blockage
    # is relevant.

# Note the new room_choices structure! Would it be better to include
# various permutations of the possible combinations after all?
# What should happen now if no full match is found?
# I suppose some fancy structure with shared sub-trees might make things
# easier here (?), but would be difficult to set up ...
# Actually, on reflection, I'm not really sure that the added complexity
# is worth it at all. Yes the tree structure requires fewer comparisons
# in general, but potentially not so very many fewer and the total
# cost may be similar or higher. Perhaps I should just accept that
# matching choice lists is time-consuming and keep it simple?
# So, revert to simple lists???
# Consider also making room allocation a purely soft constraint, though
# perhaps with an especially large penalty for "+"-weighting.
# Actually, wouldn't purely hard make more sense? In the end, the lessons
# will need their rooms! The big question is, at what stage the checks
# should be done, especially as handling the room-choice lists could be
# quite "expensive". It is probably important to take into account that
# the satisfaction of room choices can be difficult and it may be
# better to leave at least tricky cases for manual handling.

# Special consideration:
# When resolving room choices manually, the possible rooms for each
# requirement should be shown, so that the one to be chosen can be
# selected. However, at present I just have a list of possible solution
# vectors. I suppose I could collect a set from each index?
# When forcing a particular room, it could be that another lesson gets
# removed, but if only a room-choice is concerned, that could also
# stay placed, but get a penalty. Would a room-choice conflict even
# count as a clash? I suppose actually not ... but if a lesson is to be
# placed and its fixed room is occupied by a choice, it should be
# possible to remove the choice and reevaluate the penalty (perform a
# reallocation). So with rooms I would need to be able to detect
# (quickly?) whether a room allocation is fixed or choice. Perhaps all
# room choices should be deallocated before an automatic placement run?
# Manual changes should not do such a deallocation (unless a fixed room
# needs to be satisfied), so there would have to be a special handler
# for this case.

    rclist = tt_lesson.room_choices
    if rclist:
        rvlen = len(rclist[0])
    else:
        return (0, [])
    best = None
    bestzeros = rvlen
    for rc in rclist:
        zeros = 0
        rl = []
        for r in rc:
            for rs in rslots:
                if rs[r] != 0:
                    rl.append(0)
                    zeros += 1
                    break
            else:
                rl.append(r)
        if zeros == 0:
            return (0, rl)
        if zeros < bestzeros:
            bestzeros = zeros
            best = rl
    # Return the "best" result, all zeros if no rooms are free.
    return (bestzeros, best or [0] * rvlen)


#########################################################

def test_placement(
    allocation: Allocation,
    tt_lesson: TT_LESSON,
    timeslot: int,
    saved_rooms: Optional[list[int]]
) -> bool:
    """Check all hard contraints for the given placement.
    """
    if critical_constraints(allocation, tt_lesson, timeslot):
        return False

#TODO: Is this at all appropriate here? Isn't it rather a question of
# whether a placement is at all possible. Saved rooms are relevant when
# entering the timetable app (or loading an alternative configuration?).
# If the saved rooms fit (and other hard constraints are satisfied) the
# placement will be done. If they don't fit, the placement will fail.
# However, note that fixed placements should probably be done first!

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


# When placing or removing a single lesson, it might be possible to
# check a greatly reduced subset of the constraints – only those
# associated directly with the lesson and those relating to the
# teachers and classgroups connected with the lesson ...
# On the other hand, it might be simpler to reevaluate all constraints.
# As this latter function probably needs to be evaluated very often, it
# would need to be reasonably fast ...
# Let's have a go at evaluating all constraints: it would probably be
# good to have the highest weightings first (hard constraints can break
# off the processing early if not fulfilled).
def place_with_room_choices(
    allocation: Allocation,
    tt_lesson: TT_LESSON,
    timeslot: int,
    saved_rooms: Optional[list[int]]
):
    """The activity is to be placed in the given time-slot.
    If a list of saved rooms is provided, try to use these.
    It is assumed that the possibility of the placement has been
    checked already!
    """
    length = tt_lesson.length
    ttli = tt_lesson.index
    state = allocation.allocation_state[ttli]
    state[0] = timeslot

    # Deal with length (number of periods)
    t = timeslot
    tmax = timeslot + length
    while t < tmax:
        # Place teachers
        pslot = allocation.teacher_weeks[t]
        for t in ttl.teachers:
            pslot[t] = ttli
        # Place class-groups
        pslot = allocation.group_weeks[t]
        for cg in ttl.classgroups:
            pslot[cg] = ttli
#TODO: comments not clear!
#TODO:  if allocation.rooms_weighting != "":
# ... if room allocation is regarded as a soft constraint ...
#           need to check whether the rooms are free!
        fixed_rooms = ttl.fixed_rooms
# Note that if also the fixed rooms can remain unsatisfied (soft room
# constraint), then I would also need to record which of these have
# been allocated – or check that the allocated rooms have really been
# assigned to the lesson in question.
# I suspect allowing the fixed rooms to be anything less than "critical"
# might cause no end of algorithmic difficulties. At what benefit? Is
# there really a scenario where this behaviour would be desirable?

        # Place single compulsory rooms
        pslot = allocation.room_weeks[t]
        # Skip the compulsory single rooms (see comment to <get_state_vector()>)
        for r in fixed_rooms:
            pslot[r] = ttli
        t += 1


    # Room choices ...
    if saved_rooms and test_room_allocation(
        allocation,
        tt_lesson.room_choices,
        saved_rooms,
        timeslot,
        tt_lesson.length
    ):
        pass


    # Deal with no saved rooms


    for rc in tt_lesson.room_choices:
        i += 1
        state[i] = 0
    #print("[]", timeslot, allocation.teacher_weeks)


def place_lesson_initial(
    allocation: Allocation,
    tt_lessons: list[Optional[TT_LESSON]],  # only the first entry is <None>
    ttli: int,
    timeslot: int,
):
    """Place the given activity in the specified time slot.
    !!! Only do this when the allocation slots are really empty, which is
    not checked here.

    allocation: placement data structures
    tt_lessons: the activity vector
    ttli: index of the activity to test (1+)
    timeslot: index of the time slot to test (1+)
    """
#TODO: Record changes – to enable their reversal.
    ttl = tt_lessons[ttli]
    #print("\n??? TTL:", ttli, timeslot)
    #print("[]", len(allocation.teacher_weeks), allocation.teacher_weeks)
    length = ttl.length
    state = allocation.allocation_state[ttli]
    state[0] = timeslot

#TODO: deal with length (number of periods)
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
#?
    # Room choices are not allocated here
    rclist = state[1]
    for i in range(len(rclist)):
        rclist[i] = 0
    #i = 0
    #for rc in ttl.room_choices:
    #    rclist[i] = 0
    #    i += 1
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
def load_timetable(tt_data, state):
    tt_lessons = tt_data.tt_lessons
    allocation = Allocation(tt_data)
    i = 0
    imax = len(tt_lessons) - 1
    while i < imax:
        i += 1
        ttl = tt_lessons[i]
        #print("???", ttl.room_choices)
        timeslot = ttl.time
        if timeslot != 0:
#TODO: Could have been "^ ..." (lesson reference)!
            blockers = critical_constraints(
                allocation, ttl, timeslot
            )
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
#TODO: room choices
            if ttl.placement0 == timeslot:
                # Remove rooms from saved list if they are in the fixed
                # list.
#TODO: Is that sensible? Maybe just fail because soething has changed?
                r0 = state[i][1]
                for r in ttl.fixed_rooms:
                    try:
                        r0.remove(r)
                    except ValueError:
                        pass
                #print("+++ CHECK ROOM CHOICES", r0)
                if not test_room_allocation(
                    allocation,
                    ttl.room_choices,
                    r0,
                    timeslot,
                    ttl.length,
                ):
                    print(
                        "??? ROOM MISMATCH: ",
                        state[i][1],
                        r0
                    )
                    print(" ~~", ttl)

        elif state:
#TODO: rather add to pending list, for processing after all fixed
# placements?

            timeslot = state[i][0]
            if timeslot == 0:
                continue
            blockers = critical_constraints(
                allocation, tt_lessons[i], timeslot
            )
#--
            print("?????", i, timeslot, blockers)

            if blockers:
                continue
        else:
            continue

# If no blockers, do the placement, otherwise add to unallocated list/map.
# When all done (?) calculate penalties?
# Penalties are only relevant when all tt_lessons have been placed ...

# What about (other) hard constraints, like room choices?
        place_lesson_initial(allocation, tt_lessons, i, timeslot)

    #for data in tt_state:
    #    print(" --", data)


def print_activity(tlesson):
    course1 = tlesson.courselist[0]
    multi = " ..." if len(tlesson.courselist) > 1 else ""
    g = f"{course1.klass}.{course1.group}"
    return f"{g}|{course1.tid}{multi} :: {tlesson.subject_tag}"


# Do I want to keep this structure?
def get_saved_state(tt_lessons) -> list[tuple[int, list[int]]]:
    """Extract the placements from the LESSONS table (via the activities
    list).
    """
    state = [(0, [])]
    for ttl in tt_lessons[1:]:
        # The rooms might not correspond (even in number) to those
        # expected ...
        if ttl.placement0 > 0:
            state.append((ttl.placement0, ttl.rooms0))
        else:
            state.append((0, []))
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
    allocation: Allocation,
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
        print("  ====> length mismatch")
        return False
    # Check availability of requested rooms
    while length > 0:
        pslot = allocation.room_weeks[timeslot]
        for r in test_rooms:
            if pslot[r] != 0:
                print("  ====> room not avaiable:", r)
                return False
        timeslot += 1
        length -= 1
    # Check that the rooms are in the requirements lists.
#TODO: Check this:
    # This assumes correct ordering!
    for i, r in enumerate(test_rooms):
        if r not in requirements[i]:
            print("  ====> choice mismatch:", test_rooms, "\n vs.", requirements)
            return False
    return True

# A more complicated alternative to the last bit (probably unnecessary):
#    # Attempt to correlate requested rooms with required rooms
#    def select(rs, ri):
#        # A recursive function
#        try:
#            rs.intersection(requirements[ri])
#        except IndexError:
#            return True # all requirements tested
#        for r in intersects.pop():
#            if select(rs - {r}, ri + 1):
#                return True
#        return False
#    return select(set(test_rooms), 0)


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

    from timetable.tt_basic_data import TimetableData
    TT_DATA = TimetableData()

    print("\n+ get_saved_state")
    state = get_saved_state(TT_DATA.tt_lessons)
    print(" ... done")
    #i = 0
    #for s in state:
    #    i += 1
    #    print("  §§", s)

    print("\n+ load timetable using saved placements")
    load_timetable(TT_DATA, state)
    print(" ... done")

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
