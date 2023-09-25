"""
timetable/tt_constraints.py

Last updated:  2023-09-25

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

# Would inheritance from a base class <Constraint> help? Or is it
# enough to provide the <evaluate> method (to adhere to the "interface")?

class MaxGapsPerDay:
# Do I want to know where exactly all breaking gaps are? Would a
# visual representation of a breakage be possible and helpful, or rather
# contribute to information overload?
# Perhaps each breakage should be recorded?
# Or perhaps it would suffice to know that this condition is broken for
# this teacher or group?
# Let's go for a simple approach first, only recording the fact of the
# breakage (not even the number of breakages).
    def __init__(self, allocation, ix, max_gaps, penalty):
        self.max_gaps = max_gaps
# Does this need processing?
        self.penalty = penalty
        self.ix = ix

# Let's do this for teachers first, class-groups might then just need
# to override __init__ (or a setup method).
        tt_data = allocation.tt_data
        self.ppd = tt_data.periods_per_day
        self.dpw = tt_data.days_per_week

        self.slots = allocation.teacher_weeks

    def evaluate():
# Move self variables to local ones?
        i = 0
        for day in self.dpw:
            # Don't count gaps at start of day
            started = False
            gaps = 0
            for p in self.ppd:
                i += 1
                if self.slots[i][self.ix] != 0:
                    started = True
                elif started:
                    gaps += 1
                    if gaps > self.max_gap:
                        return self.penalty
        return 0
