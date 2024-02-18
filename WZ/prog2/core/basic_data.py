"""
core/basic_data.py - last updated 2024-02-18

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

DATABASE = "wznew.sqlite"

########################################################################

import os

if __name__ == "__main__":
    import sys

    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(basedir)

from core.base import Tr
T = Tr("core.basic_data")

### +++++

from typing import Any
from shutil import copyfile
from datetime import date, timedelta, datetime
from glob import glob
import json

from core.base import (
    year_data_path,
    DATAPATH,
    REPORT_INFO,
    REPORT_ERROR,
    REPORT_CRITICAL,
)
from core.db_access import Database

__DB = None           # the current database, set in "get_database"
CONFIG = None
CALENDAR = None

REPORT_SPLITTER = '#'
REPORT_ALL_NAMES = '*'
SUBJECT_SPLITTER = '*'

ISOTIME = "%Y-%m-%d"    # iso time format for datetime.strptime, etc.

### -----


def to_json(item):
    return json.dumps(item, ensure_ascii = False, separators = (',', ':'))


def get_database(year: str = None):
    global __DB, CONFIG, CALENDAR
    if year or not __DB:
        __DB = YearData(year)
        CONFIG = __DB.CONFIG
        CALENDAR = __DB.CALENDAR
    return __DB


class YearData(Database):
    __slots__ = (
        "nodes", "tables", "CONFIG", "CALENDAR", "__tables",
        "modified_ids", "trigger_update"
    )

    def __init__(self, year: str, trigger_update = None):
        self.modified_ids = set()
        self.trigger_update = trigger_update

        ## Open the database
        if year:
            dbpath = year_data_path(year, path = DATABASE)
        else:
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
                bu = False
                # Find last backup:
                bulist = glob(DATAPATH(f"BACKUP/*_{DATABASE}"))
                if bulist:
                    bulist.sort()
                    bupath0 = bulist[-1]
                    budate = date.fromtimestamp(os.path.getmtime(bupath0))
                    dbdate = date.fromtimestamp(os.path.getmtime(dbpath))
                    if dbdate > budate:
                        # Changed since old backup, create new backup
                        bu = True
                        ## Delete excess backup
                        #if len(bulist) > 4:
                        #    os.remove(bulist[0])
                else:
                    # No backups, create one
                    bu = True
                if bu:
                    os.makedirs(os.path.dirname(bupath), exist_ok = True)
                    copyfile(dbpath, bupath)
                    REPORT_INFO(T("MONTHLY_DB_BACKUP", path = bupath))

        ## Load the database
        super().__init__(dbpath)
        # Read all "nodes"
        tables = {}
        record_map = {}
        self.nodes = record_map
        for id, table, data in self.select("* from NODES"):
            record_map[id] = NODE(table, id, self, **json.loads(data))
            try:
                tables[table].append(id)
            except KeyError:
                tables[table] = [id]
        self.tables = tables
        # Set up the CONFIG table
        self.CONFIG = _CONFIG(self)
        # ... and the CALENDAR table
        self.CALENDAR = _CALENDAR(self)
        self.__tables = {}

    def table(self, name):
        try:
            return self.__tables[name]
        except KeyError:
            try:
                cls = DB_Table._table_classes[name]
            except KeyError:
                REPORT_CRITICAL(f"Bug: Table {name} not registered")
        tbl = cls(self)
        self.__tables[name] = tbl
        return tbl

    def add_node(self, table, **new):
        id = self.insert(
            "NODES",
            ("DB_TABLE", "DATA"),
            (table, to_json(new))
        )
        self.nodes[id] = NODE(table, id, self, **new)
        self.tables[table].append(id)

    def modified(self, id: int):
        self.modified_ids.add(id)
        if self.trigger_update:
            self.trigger_update()
        else:
            self.update_nodes()

    def update_nodes(self):
        """Save modifications to database.
        """
        while True:
            try:
                id = self.modified_ids.pop()
            except KeyError:
                break
            node = self.nodes[id]
            self.update("NODES", id, "DATA", to_json(node))


class NODE(dict):
    """A special <dict> for NODES records.
    It supports attribute access and handles automatic redirection of
    references to other NODE records via reference field names stripped
    of the "_id" suffix.
    Only fields entered at initialization, or later using the method <set>,
    are available.
    """
    __slots__ = ("_table", "_id", "_db")

    def __init__(self, table: str, id: int, db: YearData, **fields):
        super().__init__()
        super().__setattr__("_table", table)
        super().__setattr__("_id", id)
        super().__setattr__("_db", db)
        self.set(**fields)

    def __getattr__(self, field: str):
        return self[field]

    def __getitem__(self, field: str):
        try:
            return super().__getitem__(field)
        except KeyError:
            r = super().__getitem__(f"{field}_id")
            try:
                return self._db.nodes[r]
            except KeyError:
                REPORT_CRITICAL(f"Bug: NODES[{r}] does not exist")

    def set(self, **fields):
        for k, v in fields.items():
            super().__setitem__(k, v)

    def set_modified(self):
        """Trigger a db update.
        """
        self._db.modified(self._id)

    def __setattr__(self, field: str, val: Any):
        if field in self.__slots__:
            super().__setattr__(field, val)
        else:
            self[field] = val

    def __setitem__(self, field: str, val: Any):
        """Updates only existing fields when the value is really new.
        Other fields will raise a <KeyError>.
        """
        if val != super().__getitem__(field):
            super().__setitem__(field, val)
            self.set_modified()


class DB_Table:
    """This is a sort of "virtual" class.
    """
    _table_classes = {}    # collect table classes
    null_entry = {}
    order = None

    @classmethod
    def add_table(cls, tableclass):
        cls._table_classes[tableclass._table] = tableclass

    def __init__(self, db):
        self.db = db
        if not db.tables.get(self._table):
            db.tables[self._table] = []
            new = {"_i": 0}
            new.update(self.null_entry)
            db.add_node(self._table, **new)
        self.setup()

    def setup(self):
        pass

    def records(self):
        olist = [
            (self.db.nodes[id], id)
            for id in self.db.tables[self._table]
        ]
        if self.order:
            olist.sort(key = lambda x: x[0][self.order])
        return olist


class _CONFIG:
    __slots__ = ("_map",)
    _table = "__CONFIG__"

    def __init__(self, year_data: YearData):
        self._map = {}
        comments = {}
        self._map["__COMMENTS__"] = comments
        for id in year_data.tables[self._table]:
            record = year_data.nodes[id]
            key = record["K"]
            comments[key] = record["COMMENT"]
            self._map[key] = record["DATA"]

    def __getattr__(self, key) -> Any:
        if key == "DECIMAL_PLACES":
            return int(self._map["DECIMAL_PLACES"])
        if key == "DECIMAL_ZERO":
            return 10**-(self.DECIMAL_PLACES + 1)
        return self._map[key]


class _CALENDAR:
    __slots__ = ("_map",)
    _table = "__CALENDAR__"

    def __init__(self, year_data: YearData):
        self._map = {}
        self._map["__HOLIDAYS__"] = {}
        self._map["__CUSTOM__"] = {}
        self._map["__REPORTS__"] = {}
        records = {}
        self._map["__RECORDS__"] = records
        for id in year_data.tables[self._table]:
            record = year_data.nodes[id]
            key = record["K"]
            d1 = record["DATE1"]
            d2 = record["DATE2"]
            comment = record["COMMENT"]
            records[key] = [d1, d2, comment, id]
            self.set_key(key, d1, d2)

    def set_key(self, key, d1, d2) -> bool:
        val = None
        if d2:
            if d2 == "X":
                # Only the first "date" is relevant, but it won't
                # be checked, to allow other formats, etc.
                val = d1
            else:
                if isodate(d2) is None:
                    REPORT_ERROR(T("BAD_DATE", key = key, date = d2))
                    return False
        if val is None:
            if isodate(d1):
                val = (d1, d2) if d2 else d1
            else:
                if d1:
                    REPORT_ERROR(T("BAD_DATE", key = key, date = d1))
                # If (also) <d1> is empty, this entry will be ignored
                return False
        key0 = key[0]
        if key0 == '_':
            self._map["__HOLIDAYS__"][key] = val
        elif key0 == '*':
            self._map["__CUSTOM__"][key] = val
        elif key0 == '.':
            self._map["__REPORTS__"][key] = val
        else:
            self._map[key] = val
        return True

    def __getattr__(self, key) -> Any:
        return self._map[key]

    def all_string_fields(self):
        return {
            f: val
            for f, val in self._map.items()
            if isinstance(val, str)
        }

    def update(
        self,
        K: str,
        DATE1: str = None,
        DATE2: str = None,
        COMMENT: str = None,
    ):
        """Update or add a new calendar entry.
        """
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
            self._map["__RECORDS__"][K] = [DATE1, d2, c]
            get_database().add_node(
                self._table,
                K = K,
                DATE1 = DATE1,
                DATE2 = d2,
                COMMENT = c
            )
            self.set_key(K, DATE1, d2)
        else:
            ## existing record
            d1, d2, comment = old_value
            changes = {}
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
                changes["DATE2"] = DATE2
                old_value[1] = DATE2
            if DATE1 is not None:
                if DATE2 != "X" and not isodate(DATE1):
                    REPORT_CRITICAL(
                        "Bug: basic_data::_CALENDAR.update"
                        f" got bad DATE1 ({DATE1})"
                    )
                changes["DATE1"] = DATE1
                old_value[0] = DATE1
            if COMMENT is not None:
                changes["COMMENT"] = COMMENT
                old_value[2] = COMMENT
            node = get_database().nodes[old_value[3]]
            node.set(**changes)
            node.set_modified()
            self.set_key(K, old_value[0], old_value[1])


def isodate(date: str) -> datetime:
    try:
        return datetime.strptime(date, ISOTIME)
    except ValueError:
        return None


def print_fix(
    value: float,
    decimal_places: int = -1,
    strip_trailing_zeros: bool = True
) -> str:
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


def fix_is_zero(value: float) -> bool:
    abs(value) < CONFIG.DECIMAL_ZERO


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
#    print("\n?DB_TABLES:", DB_TABLES)

    db = get_database()

    r = NODE("Table", 1000, db, the_other = "The other", ref_id = 3)
#    r._table = "that"
    print(r._table, r._id)
    print(r.get("_table"))
    r.set(extra = "Extra")
    print(r)
    print("JSON:", to_json(r))
    print(r.get("x"))
    print("$", r.ref)
#    print(r.x)

    print("\n§CONFIG:")
    comments = CONFIG._map.pop("__COMMENTS__")
    for k, v in CONFIG._map.items():
        print(" --", k, "::", repr(v), "//", comments.get(k))
    print(f"\n  DECIMAL_PLACES: {repr(CONFIG.DECIMAL_PLACES)}")
    print(f"  DECIMAL_ZERO: {repr(CONFIG.DECIMAL_ZERO)}")

    print("\n§CALENDAR:")
    for k, v in CALENDAR._map.items():
        print(" --", k, "::", repr(v))

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
