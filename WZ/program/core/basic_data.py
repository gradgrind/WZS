"""
core/basic_data.py - last updated 2024-01-21

Configuration and other basic data dependent on the database.


==============================
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
"""

DATABASE = "wz.sqlite"

########################################################################

import os

if __name__ == "__main__":
    import sys

    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import Tr
T = Tr("core.basic_data")

### +++++

from typing import Any
from shutil import copyfile
from datetime import date, timedelta, datetime
from glob import glob

from core.base import (
    DATAPATH,
    REPORT_INFO,
    REPORT_ERROR,
)
from core.db_access import (
    Database,
    DB_TABLES,
    db_Table,
    DB_PK,
    DB_FIELD_TEXT,
)

__DB = None # the current database, set in "get_database"
# "CONFIG" is a {key: value} configuration mapping for the current database
#CONFIG: dict[str, Any] = {}
REPORT_SPLITTER = '#'
REPORT_ALL_NAMES = '*'
SUBJECT_SPLITTER = '*'

ISOTIME = "%Y-%m-%d"    # iso time format for datetime.strptime, etc.

### -----

def get_database():
    def db_backup():
        os.makedirs(os.path.dirname(bupath), exist_ok = True)
        copyfile(dbpath, bupath)
        REPORT_INFO(T("MONTHLY_DB_BACKUP", path = bupath))

    global __DB
    if __DB is None:
        dbpath = DATAPATH(DATABASE)
        if os.path.isfile(dbpath):
            ## Handle backups
            # Basically, for every new month there should be a backup for the
            # last month, unless the data has not changed since the last
            # backup.
            # Get the previous month via its last day:
            t = date.today()
            dpre = date(t.year, t.month, 1) - timedelta(days = 1)
            bud = f"{dpre.year}-{dpre.month}"
            # Path to "current" backup file:
            bupath = DATAPATH(f"BACKUP/{bud}_{DATABASE}")
            if not os.path.isfile(bupath):
                # Find last backup:
                bulist = glob(DATAPATH(f"BACKUP/*_{DATABASE}"))
                if bulist:
                    bulist.sort()
                    bupath0 = bulist[-1]
                    budate = date.fromtimestamp(os.path.getmtime(bupath0))
                    dbdate = date.fromtimestamp(os.path.getmtime(dbpath))
                    if dbdate > budate:
                        # Changed since old backup, create new backup
                        db_backup()
                        ## Delete excess backup
                        #if len(bulist) > 4:
                        #    os.remove(bulist[0])
                else:
                    # No backups, create one
                    db_backup()
        # Open database
        __DB = Database(dbpath)
        # Set up the CONFIG table
        CONFIG.init(__DB)
        # ... and the CALENDAR table
        CALENDAR.init(__DB)
    return __DB


class _CONFIG:
    def __init__(self):
        self._map = {}

    def init(self, db):
        self._map.clear()
        for rec in db.table("__CONFIG__").records:
            self._map[rec.KEY] = rec.VALUE
        self.DECIMAL_PLACES = int(self._map.pop("DECIMAL_PLACES"))
        self.DECIMAL_ZERO = 10**-(self.DECIMAL_PLACES + 1)

    def __getattr__(self, key) -> Any:
        return self._map[key]
#+
CONFIG = _CONFIG()


class _CALENDAR:
    def __init__(self):
        self._map = {}

    def init(self, db):
        self._map.clear()
        hols = []
        cstmap = {}
        reports = {}
        self._map["__HOLIDAYS__"] = hols
        self._map["__CUSTOM__"] = cstmap
        self._map["__REPORTS__"] = reports
        for rec in db.table("__CALENDAR__").records:
            key = rec.KEY
            d1, d2 = rec.DATE1, rec.DATE2
            if not d1:
                continue
            val = None
            if d2:
                if d2 == "X":
                    # Only the first "date" is relevant, but it won't
                    # be checked, to allow other formats, etc.
                    val = d1
                else:
                    if isodate(d2) is None:
                        REPORT_ERROR(T("BAD_DATE", key = key, date = d2))
                        continue
            if val is None:
                if isodate(d1) is None:
                    REPORT_ERROR(T("BAD_DATE", key = key, date = d1))
                    continue
                val = (d1, d2) if d2 else d1
            key0 = key[0]
            if key0 == '_':
                # Holidays
                hols.append(val)
            elif key0 == '*':
                # "Custom" values
                cstmap[key[1:]] = val
            elif key0 == '.':
                # Date for reports, etc.
                reports[key[1:]] = val
            else:
                self._map[key] = val
        #print("§CALENDAR:", self._map)

    def __getattr__(self, key) -> Any:
        return self._map[key]

    def all_string_fields(self):
        return {
            f: val
            for f, val in self._map.items()
            if isinstance(val, str)
        }
#+
CALENDAR = _CALENDAR()


def isodate(date: str) -> datetime:
    try:
        return datetime.strptime(date, ISOTIME)
    except ValueError:
        return None


def print_fix(
    value: float,
    decimal_places: int = -1,
    strip_trailing_zeros : bool = True) -> str:
    """Print a "float" in a fixed-point way.
    "decimal_places" specifies how many are to be printed (>= 0). The
    number is rounded to this precision. If "decimal_places" is negative,
    "CONFIG.DECIMAL_PLACES" will be used.
    If "strip_trailing_zeros" is true, exactly that will be done. If there
    are then no decimal places left, also the decimal separator will be
    removed.
    """
    if decimal_places < 0:
        decimal_places = CONFIG.DECIMAL_PLACES
    fstr = f"{value:.{decimal_places}f}"
    if decimal_places:
        if strip_trailing_zeros:
            i = -1
            while True:
                n = fstr[i]
                if n == '0':
                    i -= 1
                    continue
                if n == '.':
                    fstr = fstr[:i]
                elif i < -1:
                    fstr = fstr[:i+1]
                break
        return fstr.replace('.', CONFIG.DECIMAL_SEP)
    return fstr
#+
def fix_is_zero(value: float) -> bool:
    abs(value) < CONFIG.DECIMAL_ZERO


class Config(db_Table):
    table = "__CONFIG__"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("KEY", unique = True),
                DB_FIELD_TEXT("VALUE"),
                DB_FIELD_TEXT("COMMENT"),
            )
            return True
        return False

    #    def __init__(self, db: Database):
    #        self.init()
    #        super().__init__(db)
#+
DB_TABLES["__CONFIG__"] = Config


class Calendar(db_Table):
    table = "__CALENDAR__"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("KEY", unique = True),
                DB_FIELD_TEXT("DATE1"),
                DB_FIELD_TEXT("DATE2"),
                DB_FIELD_TEXT("COMMENT"),
            )
            return True
        return False
#+
DB_TABLES["__CALENDAR__"] = Calendar


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    print("\n?DB_TABLES:", DB_TABLES)

    db = get_database()

    print("\n?CONFIG:")
    print(f"  SCHOOL: {repr(CONFIG.SCHOOL)}")
    print(f"  DECIMAL_SEP: {repr(CONFIG.DECIMAL_SEP)}")
    print(f"  DECIMAL_PLACES: {repr(CONFIG.DECIMAL_PLACES)}")
    print(f"  DECIMAL_ZERO: {repr(CONFIG.DECIMAL_ZERO)}")

    print("§N 6.789@3:", print_fix(6.789, 3))
    print("§N 6.780@3:", print_fix(6.780, 3))
    print("§N 6.700@3:", print_fix(6.700, 3))
    print("§N 6.000@3:", print_fix(6.000, 3))
    print("§N 6.000@3/False:", print_fix(6.000, 3, False))
    print("§N 60.000@3:", print_fix(60.000, 3))
    print("§N 6.789@0:", print_fix(6.789, 0))
    print("§N 6.789@1:", print_fix(6.789, 1))
    print("§N 6.789@2:", print_fix(6.789, 2))
