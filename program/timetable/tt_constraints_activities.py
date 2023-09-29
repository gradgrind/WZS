"""
timetable/tt_constraints_activities.py

Last updated:  2023-09-29

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

#from typing import NamedTuple, Optional

#from core.basic_data import get_days, get_periods
#from timetable.tt_basic_data import TT_LESSON

### -----

    * At start/end of day
        # h (H for start?), S
        (?)
        (ConstraintActivityEndsStudentsDay)

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
        self.groups = tt_data.tt_lessons.classgroups
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
        self.groups = tt_data.tt_lessons.classgroups
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





#    * Not on same day
#        # H, S
#    * Min days between (combine with not-on-same-day?)
#        # H, S
#        (ConstraintMinDaysBetweenActivities)
#    * Not after (with or without intervening periods?)
#        # H, S
#        (ConstraintTwoActivitiesOrderedIfSameDay)
#    * Not consecutive (ConstraintMinGapsBetweenActivities)


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
#TODO: The version with multiple accceptable start times must be
# implemented as a constraint here.

#TODO:
#*** ConstraintActivitiesPreferredStartingTimes (e.g. double lesson start times)

#TODO:
#*** ConstraintActivitiesSameStartingTime
# Would it make sense to have a special implementation for the "hard"
# version of the constraint?



