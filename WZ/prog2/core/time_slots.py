"""
core/time_slots.py - last updated 2024-02-26

Manage time slot information (for timetable).

=+LICENCE=================================
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
=-LICENCE=================================
"""

import sys, os

if __name__ == "__main__":
    # Enable package import if running as module
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(basedir)

#from core.base import Tr
#T = Tr("core.time_slots")

### +++++

from typing import NamedTuple

from core.basic_data import DB_Table


class TIMESLOT(NamedTuple):
    """Note that the <day> and <period> fields are intended for indexing
    purposes, so that the first (real) entry is 0.
    To get the corresponding id-keys for the day and period mappings, 1
    must be added – as the 0-indexed entry of these is regarded as
    "invalid", their first "real" entry has id = 1.
    """
    day: int
    period: int
    NAME: str

### -----


class Days(DB_Table):
    __slots__ = ()
    _table = "TT_DAYS"
    null_entry = {"TAG": "", "NAME": ""}
    order = "#"


DB_Table.add_table(Days)


class Periods(DB_Table):
    __slots__ = ()
    _table = "TT_PERIODS"
    null_entry = {"TAG": "", "NAME": "", "START_TIME": "", "END_TIME": ""}
    order = "#"


DB_Table.add_table(Periods)


def timeslots() -> list[TIMESLOT]:
    """Return an ordered list of TIMESLOT items.
    The first item is a "null" entry.
    """
    ts = [TIMESLOT(-1, -1, "")]
    periods = [
        (p - 1, node.TAG)
        for p, node in enumerate(DB("TT_PERIODS").records())
        if p
    ]
    for d, node in enumerate(DB("TT_DAYS").records()):
        if d:
            for p, ptag in periods:
                ts.append(TIMESLOT(d - 1, p, f"{node.TAG}.{ptag}"))
    return ts


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import DB

    print("\n§Days:")
    for r in DB("TT_DAYS").records():
        print("  --", r)

    print("\n§Periods:")
    for r in DB("TT_PERIODS").records():
        print("  --", r)

    print("\n§Timeslots:")
    for t in timeslots():
        print("  --", t)
