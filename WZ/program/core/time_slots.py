"""
core/time_slots.py - last updated 2023-11-23

Manage time slot information (for timetable).

=+LICENCE=================================
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
    setup(os.path.join(basedir, 'TESTDATA'))

#from core.base import TRANSLATIONS
#T = TRANSLATIONS("core.time_slots")

### +++++

from typing import NamedTuple

from core.base import REPORT_CRITICAL

from core.db_access import (
    DB_TABLES,
    db_Table,
    db_TableRow,
    DB_PK,
    DB_FIELD_TEXT,
    DB_FIELD_REFERENCE,
)

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


class Days(db_Table):
    table = "TT_DAYS"
    order = "id"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("TAG"),
                DB_FIELD_TEXT("NAME"),
            )
            return True
        return False

DB_TABLES[Days.table] = Days


class Periods(db_Table):
    table = "TT_PERIODS"
    order = "id"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("TAG"),
                DB_FIELD_TEXT("NAME"),
                DB_FIELD_TEXT("START_TIME"),
                DB_FIELD_TEXT("END_TIME"),
            )
            return True
        return False

DB_TABLES[Periods.table] = Periods


class TimeSlots(db_Table):
    """Reader for time-slots information.
    An instance of this class manages information about the daily lesson
    periods, and the weekdays for the timetable.
    It also manages a time-slot vector covering the whole week.
    """
    table = "TT_TIME_SLOTS"
    order = "id"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_REFERENCE("Day", target = Days.table),
                DB_FIELD_REFERENCE("Period", target = Periods.table),
            )
            return True
        return False

    def timeslot(self, record: db_TableRow) -> TIMESLOT:
        dx = record.Day.id
        d = record.Day.TAG
        px = record.Period.id
        p = record.Period.TAG
        return TIMESLOT(dx-1, px-1, f"{d}.{p}" if dx > 0 else "")

    def get_timeslots(self):
        """Return (all) the timeslots as a list of TIMESLOT items.
        The first item is a "null" timeslot.
        """
        try:
            ts = self.__timeslots
            if ts:
                return ts
        except AttributeError:
            ts = []
            self.__timeslots = ts
        for i, row in enumerate(self.records):
            if row.id != i:
                REPORT_CRITICAL(
                    "Bug: Indexing in table TT_TIME_SLOTS is broken."
                    " The 'rowid' is expected to run contiguously,"
                    " starting at 0 (which is a 'null' entry)."
                )
            if i:
                dx = row.Day.id
                d = row.Day.TAG
                px = row.Period.id
                p = row.Period.TAG
                ts.append(TIMESLOT(dx-1, px-1, f"{d}.{p}"))
            else:
                ts.append(TIMESLOT(-1, -1, ""))
        return ts

    def clear_caches(self):
        # Note that the caches must be cleared if the table is changed.
        self.__timeslots = []

DB_TABLES[TimeSlots.table] = TimeSlots


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    db = get_database()

    ts = TimeSlots(db)

    print("\n******* DAYS:")
    for tdata in db.table("TT_DAYS").records:
        print(f"  {tdata}")

    print("\n******* PERIODS:")
    for tdata in db.table("TT_PERIODS").records:
        print(f"  {tdata}")

    print("\n ************** TIME-SLOTS ***********************")
    for i, ts in enumerate(ts.get_timeslots()):
        print(f"  {i:2}:", ts)

    dbts = db.table("TT_TIME_SLOTS")
    print("\n 0 ->", dbts.timeslot(dbts.records[0]))
    print("\n 3 ->", dbts.timeslot(dbts.records[3]))
