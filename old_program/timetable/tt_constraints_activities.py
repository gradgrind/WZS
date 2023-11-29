"""
timetable/tt_constraints_activities.py

Last updated:  2023-10-01

Implementation of the timetable constraints.


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

#T = TRANSLATIONS("timetable.tt_constraints")

### +++++

### -----

#TODO: Should this really allow previous empty slots?
class ActivityStartsDay:
    """This constraint checks that the activity is the first lesson of
    the day for the group concerned.
    """
    def __init__(self, allocation, aix, weight):
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        tt_data = allocation.tt_data
        self.slots = allocation.group_weeks
        self.groups = tt_data.tt_lessons[aix].classgroups
        self.ppd = tt_data.periods_per_day
        #self.dpw = tt_data.days_per_week
        self.state = allocation.allocation_state[aix]

    def evaluate():
# This allows preceding free lessons.
        timeslot = self.state[0]
        for i in range((timeslot - 1) % self.ppd):
            timeslot -= 1
            gslots = self.slots[timeslot]
            for g in self.groups:
                if gslots[g] > 0:
                    return self.penalty
        return 0


class ActivityEndsDay:
    """This constraint checks that the activity is the last lesson of
    the day for the group concerned.
    """
    def __init__(self, allocation, aix, weight):
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.aix = aix
        tt_data = allocation.tt_data
        self.slots = allocation.group_weeks
        self.groups = tt_data.tt_lessons[aix].classgroups
        self.ppd = tt_data.periods_per_day
        #self.dpw = tt_data.days_per_week
        self.state = allocation.allocation_state[aix]

    def evaluate():
        # This is made more complicated by the possibility that the
        # lesson length > 1. I can check for different activities
        # following on the same day.
        timeslot = self.state[0]
        p = (timeslot - 1) % self.ppd
        for i in range((p + 1), self.ppd):
            timeslot += 1
            gslots = self.slots[timeslot]
            for g in self.groups:
                aix = gslots[g]
                if aix > 0 and aix != self.aix:
                    return self.penalty
        return 0


class ActivitiesNotOnSameDay:
    """This constraint checks that the activities are on different
    days of the week.
    """
    def __init__(self, allocation, aixlist, weight):
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        #self.dpw = tt_data.days_per_week
        self.states = [allocation.allocation_state[i] for i in aixlist]

    def evaluate():
        days = []
        for state in self.states:
            t = self.states[0]
            if t > 0:
                d = (t - 1) // self.ppd
                if d in days:
                    return self.penalty
                days.append(d)
        return 0


class ActivitiesMinDaysBetween:
    """This constraint checks that the activities are on different
    days of the week with at least the given gap. The gap should be at
    least 2, as a single-day gap is probably better covered by
    <ActivitiesNotOnSameDay>.
    It is restricted to two activities, to keep it simple – and because
    it is assumed that more than two activities is an unlikely wish,
    given the probable shortness of the week.
    """
    def __init__(self, allocation, aix1, aix2, mindays, weight):
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.mindays = mindays
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        #self.dpw = tt_data.days_per_week
        self.state1 = allocation.allocation_state[aix1]
        self.state2 = allocation.allocation_state[aix2]

    def evaluate():
        t1, t2 = self.state1[0], self.state2[0]
        if (
            t1 > 0
            and t2 > 0
            and abs((t1 - 1) // self.ppd - (t2 - 1) // self.ppd) < self.mindays
        ):
            return self.penalty
        return 0


class ActivityNotAfter:
    """This constraint checks that the first activity is not after the
    second activity on the same day.
    """
#TODO: Should this apply only to the slot immediately after the earlier
# activity?
    def __init__(self, allocation, aix, aix0, weight):
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        #self.dpw = tt_data.days_per_week
        self.state = allocation.allocation_state[aix]
        self.state0 = allocation.allocation_state[aix0]

    def evaluate():
        t, t0 = self.state[0], self.state0[0]
        if t0 > 0 and t > t0:   # <t> after <t0>
            if (t - 1) // self.ppd == (t0 - 1) // self.ppd: # same day
                return self.penalty
        return 0


class ActivitiesMinGap:
    """This constraint checks that there is a minimum gap between a
    pair of activities.
    """
    def __init__(self, allocation, aix1, aix2, mingap, weight):
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        tt_data = allocation.tt_data
        self.gap1 = tt_data.tt_lessons[aix1].length + mingap
        self.gap2 = tt_data.tt_lessons[aix2].length + mingap
        self.ppd = tt_data.periods_per_day
        #self.dpw = tt_data.days_per_week
        self.state1 = allocation.allocation_state[aix1]
        self.state2 = allocation.allocation_state[aix2]

    def evaluate():
        t1, t2 = self.state1[0], self.state2[0]
        if t1 > 0 and t2 > 0:
            d1, p1 = divmod((t1 - 1), self.ppd)
            d2, p2 = divmod((t2 - 1), self.ppd)
            if d1 == d2:
                if p2 > p1:
                    if p1 + self.gap1 > p2:
                        return self.penalty
                elif p2 + self.gap2 > p1:
                    return self.penalty
        return 0


class ActivityPreferredStartingTimes:
    """This constraint checks that there is a minimum gap between a
    pair of activities.
    <times> is a list of 0-based period indexes.
    """
    def __init__(self, allocation, aix, times, weight):
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        tt_data = allocation.tt_data
        self.times = times
        self.ppd = tt_data.periods_per_day
        #self.dpw = tt_data.days_per_week
        self.state = allocation.allocation_state[aix]

    def evaluate():
        t = self.state1[0]
        if t > 0 and ((t - 1) % self.ppd not in self.times):
            return self.penalty
        return 0


class ActivitiesSameStartingTime:
    """This constraint checks that the activities start at the same time.
    """
    def __init__(self, allocation, aixlist, weight):
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.times = times
        self.states = [allocation.allocation_state[i] for i in aixlist]

    def evaluate():
        t = 0
        for s in self.states:
            tt = s[0]
            if tt != t and tt > 0:
                if t > 0:
                    return self.penalty
                t = tt
        return 0
#TODO: Should multiple breakages result in multiple penalties?
#        t = 0
#        p = 0
#        for s in self.states:
#            tt = s[0]
#            if tt != t and tt > 0:
#                if t > 0:
#                    p += self.penalty
#                else:
#                    t = tt
#        return p

#TODO: Would it make sense to have a special implementation for the "hard"
# version of the constraint?
# Activities should only be allowed to be parallel if there are no
# awkward clashes, like teachers, groups, fixed rooms. Also other
# constraints might be at least threatened, but it might be difficult to
# test these for conflicts.
# There could be some sort of activity-group for checking that all the
# parallel activities can be placed before any one of them is actually
# placed. One possibility might be combined teacher, group and room
# lists like for blocks. Alternatively there could be a tied-to field
# referring to another activity which is to be placed simultaneously
# (presumably only with "hard" weighting).


#*** ConstraintActivityPreferredRoom(s)
# Handled by the special room constraint functions.

#*** ConstraintStudentsSetNotAvailableTimes
#*** ConstraintTeacherNotAvailableTimes
# At present I am assuming that "hard" non-available slots contain -1.
#TODO: The soft version must be implemented as a constraint here.

#*** ConstraintActivityPreferredStartingTime(s)
# The version with a single fixed time and weight "+". is handled
# by the initial placement function.
#TODO: Is this constraint also available in a "soft" form?
# My gui doesn't at present provide for a weighting of this constraint.
# When might it make sense?

#TODO:?
#*** ConstraintActivitiesPreferredStartingTimes (e.g. double lesson start times)
# This could be done using multiple single-activity constraints and it
# is not clear that a multiple-activity constraint would help much.



