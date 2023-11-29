"""
timetable/tt_constraints_participants.py

Last updated:  2023-09-29

Implementation of the timetable constraints for student groups and teachers.


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

# It should be possible to detect blocking lessons automatically so that
# the placement of a particular lesson can be forced. Perhaps not the
# room choices, though?

# Would inheritance from a base class <Constraint> help? Or is it
# enough to provide the <evaluate> method (to adhere to the "interface")?


#deprecated?
class MaxGapsPerDay_Teacher:
    """This constraint checks that at most the given number of
    time-slots is free on each day. In this case, "unavailable" doesn't
    count as free, but also not as occupied.
    """
# Do I want to know where exactly all breaking gaps are? Would a
# visual representation of a breakage be possible and helpful, or rather
# contribute to information overload?
# Perhaps each breakage should be recorded?
# Or perhaps it would suffice to know that this condition is broken for
# this teacher or group?
# Let's go for a simple approach first, only recording the fact of the
# breakage (not even the number of breakages).
    def __init__(self, allocation, ix, max_gaps, weight):
        self.max_gaps = max_gaps
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.ix = ix # index of the slot-owner to be tested
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        self.dpw = tt_data.days_per_week
        self.setup(allocation)

    def setup(self, allocation):
        self.slots = allocation.teacher_weeks

    def evaluate():
# Move self variables to local ones?
        d = 1
        for day in range(self.dpw):
            # Don't count gaps at start of day or at end of day.
            # Initially, <pending> is -1, indicating "no lessons yet".
            # Afer a lesson has been found, <pending> is used to count
            # the length of a gap. When the next lesson is found, this
            # gap length is added to the accumulator, <gaps>.
            pending = -1
            gaps = 0
            for p in range(self.ppd):
                aix = self.slots[d + p][self.ix]
                if aix > 0:     # (using -1 for hard-blocked slots?)
                    if pending > 0:
                        gaps += pending
                        if gaps > self.max_gap:
                            return self.penalty
                    pending = 0
                elif pending >= 0:
                    pending += 1
            d += self.ppd
        return 0

class MaxGapsPerDay_Group(MaxGapsPerDay_Teacher):
    def setup(self, allocation):
        self.slots = allocation.group_weeks

# ... or both could be a subset of a sort of virtual class ...



#TODO: Actually, it would surely make sense to combine the weekly and
# daily versions, the algorithms being basically the same. Of course
# if only one of the two was used for a particular teacher, it might be
# better to keep them separate.
# Would it be reasonable to use a single penalty? In the case of a "hard"
# constraint, there would probably be no difference. Even for "soft"
# constraints it might be a reasonable compromise – worth a try.
# There is (then) no point in setting max_gaps_weekly <= max_gaps_daily.
# In that case, max_gaps_daily could be ignored here.
class MaxGaps_Teacher:
    """This constraint checks that at most the given number of
    time-slots is free in each day or week. In this case, an
    "unavailable" time-slot doesn't count as free, but also not as
    occupied.
    """
# Do I want to know where exactly all breaking gaps are? Would a
# visual representation of a breakage be possible and helpful, or rather
# contribute to information overload?
# Perhaps each breakage should be recorded?
# Or perhaps it would suffice to know that this condition is broken for
# this teacher or group?
# Let's go for a simple approach first, only recording the fact of the
# breakage (not even the number of breakages).
# Should gaps at the beginning of the day be counted? Or should that be
# a separate constraint? For the moment I'll assume it should be
# separate.
    def __init__(
        self,
        allocation,
        ix,
        max_gaps_daily,
        max_gaps_weekly,
        weight
    ):
        self.max_gaps_daily = max_gaps_daily
        self.max_gaps_weekly = max_gaps_weekly
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.ix = ix # index of the slot-owner to be tested
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        self.dpw = tt_data.days_per_week
        self.setup(allocation)

    def setup(self, allocation):
        self.slots = allocation.teacher_weeks

    def evaluate():
# Move self variables to local ones?
        d = 1
        wgaps = 0   # weekly gaps
        for day in range(self.dpw):
            # Don't count gaps at start of day or at end of day.
            # Initially, <pending> is -1, indicating "no lessons yet".
            # Afer a lesson has been found, <pending> is used to count
            # the length of a gap. When the next lesson is found, this
            # gap length is added to the accumulator, <gaps>.
            pending = -1
            gaps = 0    # daily gaps
            for p in range(self.ppd):
                aix = self.slots[d + p][self.ix]
                if aix > 0:     # (using -1 for hard-blocked slots?)
                    if pending > 0:
                        gaps += pending
#TODO: Handle constraint-not-set (by means of a large max value?)
                        if gaps > self.max_gaps_daily:
                            return self.penalty
                        wgaps += pending
                        if wgaps > self.max_gaps_weekly:
                            return self.penalty
                    pending = 0
                elif pending >= 0:
                    pending += 1
            d += self.ppd
        return 0

class MaxGaps_Group(MaxGaps_Teacher):
    def setup(self, allocation):
        self.slots = allocation.group_weeks

# ... or both could be a subset of a sort of virtual class ...


class LunchBreak_Teacher:
    """This constraint checks that at least one of a selection of
    time-slots is free on each day. In this case, "unavailable" also
    counts as free.
    """
    def __init__(self, allocation, ix, lunch_slots, weight):
        """<lunch_slots> is a list of period indexes (0-based).
        """
        self.ix = ix # index of the slot-owner to be tested
#TODO: Rather get the slots from config / db?
        self.lunch_slots = lunch_slots
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        self.dpw = tt_data.days_per_week
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.setup(allocation)

    def setup(self, allocation):
        self.slots = allocation.teacher_weeks

    def evaluate(self):
        d = 1
        for day in range(self.dpw):
            for p in self.lunch_slots:
                # (using -1 for hard-blocked slots?)
                if self.slots[d + p][self.ix] <= 0:
                    break
            else:
                return self.penalty
            d += self.ppd
        return 0

class LunchBreak_Group(LunchBreak_Teacher):
    def setup(self, allocation):
        self.slots = allocation.group_weeks

# ... or both could be a subset of a sort of virtual class ...


class MinLessonsPerDay_Teacher:
    """This constraint checks that there are at least the given number
    of lessons in each day.
    """
# Do I want to know which days break the constraint? Would a
# visual representation of a breakage be possible and helpful, or rather
# contribute to information overload?
# Perhaps each breakage should be recorded?
# Or perhaps it would suffice to know that this condition is broken for
# this teacher or group?
# Let's go for a simple approach first, only recording the fact of the
# breakage (not even the number of breakages).
    def __init__(
        self,
        allocation,
        ix,
        min_lessons_daily,
        weight
    ):
        self.min_lessons_daily = min_lessons_daily
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.ix = ix # index of the slot-owner to be tested
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        self.dpw = tt_data.days_per_week
        self.setup(allocation)

    def setup(self, allocation):
        self.slots = allocation.teacher_weeks

    def evaluate():
# Move self variables to local ones?
        d = 1
        for day in range(self.dpw):
            lessons = 0    # lessons on current day
            for p in range(self.ppd):
                aix = self.slots[d + p][self.ix]
                if aix > 0:     # (using -1 for hard-blocked slots?)
                    lessons += 1
                    if lessons >= self.min_lessons_daily:
                        break
            else:
                return self.penalty
            d += self.ppd
        return 0

class MinLessonsPerDay_Group(MinLessonsPerDay_Teacher):
    def setup(self, allocation):
        self.slots = allocation.group_weeks

# ... or both could be a subset of a sort of virtual class ...


class MaxLessonsPerDay_Teacher:
    """This constraint checks that there are at most the given number
    of lessons in each day.
    """
# Do I want to know which days break the constraint? Would a
# visual representation of a breakage be possible and helpful, or rather
# contribute to information overload?
# Perhaps each breakage should be recorded?
# Or perhaps it would suffice to know that this condition is broken for
# this teacher or group?
# Let's go for a simple approach first, only recording the fact of the
# breakage (not even the number of breakages).
    def __init__(
        self,
        allocation,
        ix,
        max_lessons_daily,
        weight
    ):
        self.max_lessons_daily = max_lessons_daily
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.ix = ix # index of the slot-owner to be tested
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        self.dpw = tt_data.days_per_week
        self.setup(allocation)

    def setup(self, allocation):
        self.slots = allocation.teacher_weeks

    def evaluate():
# Move self variables to local ones?
        d = 1
        for day in range(self.dpw):
            lessons = 0    # lessons on current day
            for p in range(self.ppd):
                aix = self.slots[d + p][self.ix]
                if aix > 0:     # (using -1 for hard-blocked slots?)
                    lessons += 1
                    if lessons > self.max_lessons_daily:
                        return self.penalty
            d += self.ppd
        return 0


class MaxLessonsPerDay_Group(MinLessonsPerDay_Teacher):
    def setup(self, allocation):
        self.slots = allocation.group_weeks

# ... or both could be a subset of a sort of virtual class ...


class MaxBlock_Teacher:
    """This constraint checks that at most the given number of
    consecutive lessons (without a break) is to be given. In this case,
    an "unavailable" time-slot counts as free.
    """
    def __init__(
        self,
        allocation,
        ix,
        max_block_length,
        weight
    ):
        self.max_blocks = max_block_length
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.ix = ix # index of the slot-owner to be tested
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        self.dpw = tt_data.days_per_week
        self.setup(allocation)

    def setup(self, allocation):
        self.slots = allocation.teacher_weeks

    def evaluate():
# Move self variables to local ones?
        d = 1
        for day in range(self.dpw):
            blen = 0
            for p in range(self.ppd):
                aix = self.slots[d + p][self.ix]
                if aix > 0:     # (using -1 for hard-blocked slots?)
                    blen += 1
                    if blen > self.max_blocks:
                        return self.penalty
                    continue
                blen = 0
            d += self.ppd
        return 0

class MaxBlock_Group(MaxGapsPerDay_Teacher):
    def setup(self, allocation):
        self.slots = allocation.group_weeks

# ... or both could be a subset of a sort of virtual class ...


class MaxDaysPerWeek_Teacher:
    """This constraint checks that there are lessons on at most the
    given number of days.
    """
    def __init__(
        self,
        allocation,
        ix,
        max_days,
        weight
    ):
        self.max_days = max_days
        self.weight = weight    # Needed for priority sorting?
#TODO: Is the penalty a simple mapping from the weight?
#        self.penalty = ???
        self.ix = ix # index of the slot-owner to be tested
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        self.dpw = tt_data.days_per_week
        self.setup(allocation)

    def setup(self, allocation):
        self.slots = allocation.teacher_weeks

    def evaluate():
# Move self variables to local ones?
        d = 1
        days = 0
        for day in range(self.dpw):
            for p in range(self.ppd):
                aix = self.slots[d + p][self.ix]
                if aix > 0:     # (using -1 for hard-blocked slots?)
                    days += 1
                    if days > self.max_days:
                        return self.penalty
                    break
            d += self.ppd
        return 0
