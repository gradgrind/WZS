"""
core/basic_data.py - last updated 2024-02-17

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
    REPORT_CRITICAL,
)
from core.db_access import (
    Database,
    DB_TABLES,
)

__DB = None # the current database, set in "get_database"
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
    __slots__ = ("_map",)
    __table = "__CONFIG__"
    _create = f"""CREATE TABLE {__table} (
        id      INTEGER PRIMARY KEY NOT NULL,
        K       TEXT    UNIQUE NOT NULL,
        DATA    TEXT    NOT NULL,
        COMMENT TEXT    NOT NULL
    )
    STRICT;
    """
    def __init__(self):
        self._map = {}

    def init(self, db):
        self._map.clear()
        comments = {}
        self._map["__COMMENTS__"] = comments
        for key, val, comment in db.select(
            f"K, DATA, COMMENT from {self.__table}"
        ):
            comments[key] = comment
            self._map[key] = val
        #print("\§CONFIG:", self._map)

    def __getattr__(self, key) -> Any:
        if key == "DECIMAL_PLACES":
            return int(self._map["DECIMAL_PLACES"])
        if key == "DECIMAL_ZERO":
            return 10**-(self.DECIMAL_PLACES + 1)
        return self._map[key]
#+
CONFIG = _CONFIG()


class _CALENDAR:
    __slots__ = ("_map",)
    __table = "__CALENDAR__"
    _create = f"""CREATE TABLE {__table} (
        id      INTEGER PRIMARY KEY NOT NULL,
        K       TEXT    UNIQUE NOT NULL,
        DATE1   TEXT    NOT NULL,
        DATE2   TEXT    NOT NULL,
        COMMENT TEXT    NOT NULL
    )
    STRICT;
    """

    def __init__(self):
        self._map = {}

    def init(self, db):
        self._map.clear()
        self._map["__HOLIDAYS__"] = {}
        self._map["__CUSTOM__"] = {}
        self._map["__REPORTS__"] = {}
        records = {}
        self._map["__RECORDS__"] = records
        for key, d1, d2, comment in db.select(
            f"K, DATE1, DATE2, COMMENT from {self.__table}"
        ):
            records[key] = [d1, d2, comment]
            self.set_key(key, d1, d2)
        #print("§CALENDAR:", self._map)

    def set_key(self, key, d1, d2):
        val = None
        if d2:
            if d2 == "X":
                # Only the first "date" is relevant, but it won't
                # be checked, to allow other formats, etc.
                val = d1
            else:
                if isodate(d2) is None:
                    REPORT_ERROR(T("BAD_DATE", key = key, date = d2))
                    return
        if val is None:
            if isodate(d1):
                val = (d1, d2) if d2 else d1
            else:
                if d1:
                    REPORT_ERROR(T("BAD_DATE", key = key, date = d1))
                # If (also) <d1> is empty, this entry will be ignored
                return
        key0 = key[0]
        if key0 == '_':
            self._map["__HOLIDAYS__"][key] = val
        elif key0 == '*':
            self._map["__CUSTOM__"][key] = val
        elif key0 == '.':
            self._map["__REPORTS__"][key] = val
        else:
            self._map[key] = val

    def __getattr__(self, key) -> Any:
        return self._map[key]

    def all_string_fields(self):
        return {
            f: val
            for f, val in self._map.items()
            if isinstance(val, str)
        }

    def update(self,
        K: str,
        DATE1: str = None,
        DATE2: str = None,
        COMMENT: str = None,
    ):
        """Update or extend database table.
        """
        db = get_database()
        try:
            old_value = self._map["__RECORDS__"][K]
        except KeyError:
            ## new record
            d2 = DATE2 or ""
            c = COMMENT or ""
            if (
                not DATE1
                or d2 != "X" and (
                    not isodate(DATE1) or (d2 and not isodate(d2))
                )
            ):
                REPORT_CRITICAL(
                    "Bug in basic_data::_CALENDAR.update, got bad data:\n"
                    f"  K: {repr(K)}\n"
                    f"  DATE1: {repr(DATE1)}\n"
                    f"  DATE2: {repr(DATE2)}\n"
                    f"  COMMENT: {repr(COMMENT)}"
                )
            flist = ["K", "DATE1", "DATE2", "COMMENT"]
            vlist = [K, DATE1, d2, c]
            self._map["__RECORDS__"][K] = [DATE1, d2, c]
            db.insert(self.__table, flist, vlist)
            self.set_key(K, DATE1, d2)
        else:
            ## existing record
            d1, d2, comment = old_value
            flist, vlist = [], []
            if DATE2 is None:
                DATE2 = d2
            else:
                if DATE2 != "X":
                    if DATE1 is None and not isodate(d1):
                        REPORT_CRITICAL(
                            "Bug: basic_data::_CALENDAR.update."
                            f" New DATE2 ({DATE2}) is incompatible with"
                            f" existing DATE1 ({d1})"
                        )
                    if DATE2 and not isodate(DATE2):
                        REPORT_CRITICAL(
                            "Bug: basic_data::_CALENDAR.update"
                            f" got bad DATE2 ({DATE2})"
                        )
                flist.append("DATE2 = ?")
                vlist.append(DATE2)
                old_value[1] = DATE2
            if DATE1 is not None:
                if DATE2 != "X" and not isodate(DATE1):
                    REPORT_CRITICAL(
                        "Bug: basic_data::_CALENDAR.update"
                        f" got bad DATE1 ({DATE1})"
                    )
                flist.append("DATE1 = ?")
                vlist.append(DATE1)
                old_value[0] = DATE1
            if COMMENT is not None:
                flist.append("COMMENT = ?")
                vlist.append(COMMENT)
                old_value[2] = COMMENT
            vlist.append(K)
            db.transaction(
                f"update {self.__table} set {', '.join(flist)} where K = ?",
                vlist
            )
            self.set_key(K, old_value[0], old_value[1])
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


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    print("\n?DB_TABLES:", DB_TABLES)

    db = get_database()

    print("\n?CONFIG:")
    comments = CONFIG._map.pop("__COMMENTS__")
    for k, v in CONFIG._map.items():
        print(" --", k, "::", repr(v), "//", comments.get(k))

    print(f"\n  DECIMAL_PLACES: {repr(CONFIG.DECIMAL_PLACES)}")
    print(f"  DECIMAL_ZERO: {repr(CONFIG.DECIMAL_ZERO)}")

    print("\n ======= print_fix =======")
    print("§N 6.789@3:", print_fix(6.789, 3))
    print("§N 6.780@3:", print_fix(6.780, 3))
    print("§N 6.700@3:", print_fix(6.700, 3))
    print("§N 6.000@3:", print_fix(6.000, 3))
    print("§N 6.000@3/False:", print_fix(6.000, 3, False))
    print("§N 60.000@3:", print_fix(60.000, 3))
    print("§N 6.789@0:", print_fix(6.789, 0))
    print("§N 6.789@1:", print_fix(6.789, 1))
    print("§N 6.789@2:", print_fix(6.789, 2))
