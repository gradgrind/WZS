"""
core/db_access.py

Last updated:  2023-08-10

Helper functions for accessing the database.

After experiencing difficulties in the handling of empty/null fields,
I am now trying to avoid NULL fields altogether. Setting empty fields to
NULL saves some space, but can lead to bugs.
Where empty foreign keys are possible (which may also be a questionable
design choice, but it seems to be convenient) I use a 0-key and a
corresponding entry in the target table.

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

DATABASE = "wzs_db.sqlite"

########################################################################

import os

if __name__ == "__main__":
    import sys

    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import start

    start.setup(os.path.join(basedir, 'TESTDATA'))

T = TRANSLATIONS("core.db_access")

### +++++

from typing import Union

from datetime import datetime
from shutil import copyfile
from glob import glob

from core.base import Dates
from ui.ui_base import (
    ### QtCore:
    QMetaType,
    ### QtSql:
    QSqlDatabase,
    QSqlQuery,
    QSqlRecord,
    QSqlField,
)
db_sqlrecord = QSqlRecord

class NoRecord(Exception):
    pass


### -----


def open_database(dbfile=None):
    """Ensure the connection to the database is open.
    The QtSql default connection is used.
    """
    if not dbfile:
        dbfile = DATABASE
    dbpath = DATAPATH(dbfile)
    bupath = DATAPATH(f"BACKUP/{Dates.today().rsplit('-', 1)[0]}_{dbfile}")
    if not os.path.isfile(bupath):
        os.makedirs(os.path.dirname(bupath), exist_ok=True)
        copyfile(dbpath, bupath)
        REPORT("INFO", T["MONTHLY_DB_BACKUP"].format(path=bupath))

    con = QSqlDatabase.database()
    if con.isValid():
        if con.databaseName() == dbpath:
            # The connection is already open
            return con
        # Connected to another db: close it
        con.close()
        connectionName = con.connectionName()
        con = None  # needed to release the database object
        QSqlDatabase.removeDatabase(connectionName)
    # Open the connection
    con = QSqlDatabase.addDatabase("QSQLITE")
    con.setDatabaseName(dbpath)
    assert con.open(), f"Cannot open database at {dbpath}"
    # print("TABLES:", con.tables())
    foreign_keys_on = "PRAGMA foreign_keys = ON"
    assert QSqlQuery(foreign_keys_on).isActive(), f"Failed: {foreign_keys_on}"
    return con


def db_name():
    """Return the "name" (file path) of the default database.
    """
    return QSqlDatabase.database().databaseName()


class DatabaseShortAccess:
    """A "context manager" for performing some commands on a database
    then closing it. The default database is not affected.
    """
    def __init__(self, dbpath, tag):
        """Open the database at the given address. <tag> should be an
        ASCII string, unique to open databases.
        """
        self.dbpath = dbpath
        self.tag = tag

    def __enter__(self):
        # Enter the context manager
        self.con = QSqlDatabase.addDatabase("QSQLITE", self.tag)
        self.con.setDatabaseName(self.dbpath)
        assert self.con.open(), f"Cannot open database at {self.dbpath}"
        foreign_keys_on = "PRAGMA foreign_keys = ON"
        assert QSqlQuery(foreign_keys_on, self.con).isActive(), (
            f"Failed: {foreign_keys_on}"
        )

    def __exit__(self, *args):
        # Exit the context manager
        self.con.close()
        self.con = None  # needed to release the database object
        QSqlDatabase.removeDatabase(self.tag)

    @classmethod
    def new_database(cls, dbpath, sql_list):
        if os.path.isfile(dbpath):
            os.remove(dbpath)
        dbdir = os.path.dirname(dbpath)
        os.makedirs(dbdir, exist_ok=True)
        db = cls(dbpath, "NEW")
        with db:
            query = QSqlQuery(db.con)
            for cmd in sql_list:
                if not query.exec(cmd):
                    error = query.lastError()
                    REPORT(
                        "ERROR", f"SQL query failed: {error.text()}\n  {cmd}"
                    )
                    assert False, "Failed: create table"


def db_backup(name=""):
    dbpath = DATAPATH(DATABASE)
    if name:
        newfile = DATAPATH(name) + ".sqlite"
    else:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        newfile = f"{dbpath}_{stamp}"
    copyfile(dbpath, newfile)
    existing = sorted(glob(dbpath + "_*"))
    msg = [T["BACKUP_TO"].format(f=newfile)]
    for f in existing[:-5]:
        msg.append(T["REMOVE_OLD_BACKUP"].format(f=f))
        os.remove(f)
    REPORT("INFO", "\n".join(msg))


"""
def table_extent(table):
    query = QSqlQuery(
        f"SELECT MAX(rowid) FROM {table}"
    )
    res = []
    while (query.next()):
        res.append(query.value(0))
    print("MAX rowid:", res)
    query = QSqlQuery(
        f"SELECT COUNT(rowid) FROM {table}"
    )
    res = []
    while (query.next()):
        res.append(query.value(0))
    print("COUNT:", res)
"""


class Record:
    def __getitem__(self, key):
        if (r := self._record).contains(key):
            return r.value(key)
        raise KeyError(f"Key {key} not in {{{self}}}")

    def get(self, key, default=None):
        if (r := self._record).contains(key):
            return r.value(key)
        return default

    def __setitem__(self, key, value):
        if (r := self._record).contains(key):
            r.setValue(key, value)
        else:
            r.append(f := QSqlField(key))
            f.setValue(value)

    def __init__(self, record: QSqlRecord):
        self._record = record

    def items(self):
        r = self._record
        return ((r.fieldName(i), r.value(i)) for i in range(r.count()))

    def __str__(self):
        return "; ".join(f"{k}: {repr(v)}" for k, v in self.items())

    def todict(self):
        r = self._record
        return {r.fieldName(i): r.value(i) for i in range(r.count())}


def db_select(query_text: str) -> list[Record]:
    query = QSqlQuery(query_text)
    if not query.isActive():
        error = query.lastError()
        REPORT("ERROR", f"SQL query failed: {error.text()}\n  {query_text}")
    records = []
    while query.next():
        records.append(Record(query.record()))
    return records


#TODO: Replace this by db_select?
def db_query(query_text):
    query = QSqlQuery(query_text)
    if not query.isActive():
        error = query.lastError()
        REPORT("ERROR", f"SQL query failed: {error.text()}\n  {query_text}")
    rec = query.record()
    nfields = rec.count()
    value_list = []
    while query.next():
        value_list.append([query.value(i) for i in range(nfields)])
    return value_list


class KeyValueList(list):
    def __init__(self, iterable, check=None):
        """Build a list which also has key -> index and key -> value methods.
        iterable:   Lists (key, value) pairs
        check:      A function taking one argument, a (key, value) pair.
                    The function checks the validity of the pair.
                    If invalid it returns <None>. If valid,
                    it returns the value, which may be transformed.
        """
        super().__init__()
        self.__check = check
        self.__map = {}
        for item in iterable:
            self.append(item)

    def append(self, item):
        assert len(item) == 2, (
            f"KeyValueList – new item is not a pair: {repr(item)}"
        )
        if self.__check is not None:
            i2 = self.__check(item)
            if i2 is None:
                return    # Value invalid
            if i2 != item[1]:
                item = (item[0], i2)
        self.__map[item[0]] = len(self)
        super().append(item)

    def index(self, key):
        return self.__map[key]

    def map(self, key):
        return self[self.__map[key]][1]

    def key_list(self):
        return list(self.__map)


def db_read_table(
    table, fields, *wheres, distinct=False, sort_field=None, **keys
):
    """Read a list of table entries.
    <fields> specifies which fields are to be read. It may be
        - null/empty (=> '*'),
        - a list of strings (field names).
    <wheres> are WHERE conditions (as strings). If there is more than
    one, they are joined by "AND".
    If <distinct> is true, the "DISTINCT" keyword is added to the query.
    <sort_field> is an optional field to sort on.
    <keys> are WHERE conditions with "=" (value is str) or "IN" (value
    is list).
    Return a list of fields and a list of records (each is a list).
    """
    where_cond = [w for w in wheres]
    for k, v in keys.items():
        if isinstance(v, str):
            where_cond.append(f'"{k}" = "{v}"')
        elif isinstance(v, int):
            where_cond.append(f'"{k}" = {v}')
        elif isinstance(v, list):
            instring = ", ".join(
                [f'"{_v}"' if isinstance(_v, str) else str(_v) for _v in v]
            )
            where_cond.append(f'"{k}" IN ( {instring} )')
        else:
            assert False, (
                f"Unexpected comparison value: '{repr(v)}' for '{k}'"
            )
    if where_cond:
        where_clause = f" WHERE {' AND '.join(where_cond)}"
    else:
        where_clause = ""
    f = ", ".join([f'"{f}"' for f in fields]) if fields else "*"
    if sort_field:
        __sortlist = [f'"{__f}"' for __f in sort_field.split(',')]
        o = f" ORDER BY {','.join(__sortlist)}"
    else:
        o = ""
    d = " DISTINCT" if distinct else ""
    qtext = f"SELECT{d} {f} FROM {table}{where_clause}{o}"
    # print("§§§", qtext)
    query = QSqlQuery(qtext)
    rec = query.record()
    nfields = rec.count()
    value_list = []
    while query.next():
        value_list.append([query.value(i) for i in range(nfields)])
    if fields:
        assert (not value_list) or len(fields) == nfields, (
            f"Wrong number of fields in record: {nfields} ≠ {len(fields)}"
        )
        return fields, value_list
    else:
        return [rec.fieldName(i) for i in range(nfields)], value_list


def db_read_full_table(table, *wheres, **keys):
    return db_read_table(table, None, *wheres, **keys)


def db_read_mappings(table, *wheres, **keys) -> list[dict]:
    """Read all fields from the given table, returning the data as a
    list of mappings.
    """
    fields, records = db_read_table(table, None, *wheres, **keys)
    return [
        {fields[i]: val for i, val in enumerate(rec)}
        for rec in records
    ]


def db_read_fields(table, fields, *wheres, **keys):
    """Read a list of fields from all records from the given table,
    the normal selection parameters (see <db_read_table>) are available.
    """
    assert fields, f"No fields passed to db_read_fields on table {table}"
    return db_read_table(table, fields, *wheres, **keys)[1]


def db_read_unique(table, fields, **keys):
    flist, rlist = db_read_table(table, fields, **keys)
    if len(rlist) == 1:
        return rlist[0]
    assert not rlist, (
        f"Table {table}, query for {repr(keys)}:\n"
        f"  {len(rlist)} records (1 expected)"
    )
    raise NoRecord


def db_read_unique_field(table, field, *wheres, **keys):
    flist, rlist = db_read_table(table, [field], *wheres, **keys)
    if len(rlist) == 1:
        return rlist[0][0]
    assert not rlist, "Record not unique"
    raise NoRecord


def db_read_unique_entry(table, *wheres, **keys):
    flist, rlist = db_read_table(table, None, *wheres, **keys)
    if len(rlist) == 1:
        return flist, rlist[0]
    assert not rlist, "Record not unique"
    raise NoRecord


def db_check_unique_entry(table, *wheres, **keys):
    try:
        db_read_unique_entry(table, *wheres, **keys)
        return True
    except NoRecord:
        return False


def db_values(table, value_field, *wheres, **keys):
    """Wrapper for db_read_table returning a single list, just the
    first fields of each record. Thus it is especially suitable when
    only a single field is to be read from the table.
    """
    fields, value_list = db_read_table(table, [value_field], *wheres, **keys)
    return [v[0] for v in value_list]


def db_key_value_list(
    table, key_field, value_field, sort_field=None, check=None
):
    """Return a <KeyValueList> of (key, value) pairs from the given
    database table.
    """
    fields, value_list = db_read_table(
        table, [key_field, value_field], sort_field=sort_field
    )
    return KeyValueList(value_list, check)


def db_update_fields(table, field_values, *wheres, **keys):
    where_cond = [w for w in wheres]
    for k, v in keys.items():
        if isinstance(v, str):
            where_cond.append(f'"{k}" = "{v}"')
        elif isinstance(v, int):
            where_cond.append(f'"{k}" = {v}')
        elif isinstance(v, list):
            instring = ", ".join(
                [f'"{_v}"' if isinstance(_v, str) else str(_v) for _v in v]
            )
            where_cond.append(f'"{k}" IN ( {instring} )')
        else:
            assert False, f"Unexpected comparison value: '{repr(v)}'"
    if where_cond:
        where_clause = f" WHERE {' AND '.join(where_cond)}"
    else:
        where_clause = ""

    fields = []
    for f, v in field_values:
        if isinstance(v, str):
            fields.append(f'"{f}" = "{v}"')
        elif isinstance(v, int):
            fields.append(f'"{f}" = {v}')
        else:
            assert False, f"Unexpected field value: '{repr(v)}' for '{f}'"

    f = ", ".join(fields)
    qtext = f"UPDATE {table} SET {f}{where_clause}"
    # print("§§§", qtext)
    query = QSqlQuery()
    if query.exec(qtext):
        n = query.numRowsAffected()
        if n == 1:
            return True
        assert n < 1, f"DB error : {n} rows updated ...\n  {qtext}"
        # No row to update
        return False
    assert False, f"DB error: {query.lastError()} ...\n  {qtext}"


def db_update_field(table, field, value, *wheres, **keys):
    return db_update_fields(table, [(field, value)], *wheres, **keys)


def sql_insert_from_dict(table, field_dict):
    flist, vlist = [], []
    for f, v in field_dict.items():
        flist.append(f'"{f}"')
        if isinstance(v, str):
            vlist.append(f'"{v}"')
        elif isinstance(v, int):
            vlist.append(f"{v}")
        else:
            assert False, f"Unexpected field value: '{repr(v)}' for '{f}'"
    return (
        f"INSERT INTO {table} ({', '.join(flist)})"
        f" VALUES ({', '.join(vlist)})"
    )


def db_new_row(table, **values):
    qtext = sql_insert_from_dict(table, values)
    # print("§§§", qtext)
    query = QSqlQuery()
    if query.exec(qtext):
        newid = query.lastInsertId()
        # print("-->", newid)
        return newid
    error = query.lastError()
    REPORT("ERROR", error.text())
    return None


def db_delete_rows(table, *wheres, **keys):
    where_cond = [w for w in wheres]
    for k, v in keys.items():
        if isinstance(v, str):
            where_cond.append(f'"{k}" = "{v}"')
        elif isinstance(v, int):
            where_cond.append(f'"{k}" = {v}')
        elif isinstance(v, list):
            instring = ", ".join(
                [f'"{_v}"' if isinstance(_v, str) else str(_v) for _v in v]
            )
            where_cond.append(f'"{k}" IN ( {instring} )')
        else:
            assert False, "Unexpected comparison value: '{repr({v})'"
    if where_cond:
        where_clause = f" WHERE {' AND '.join(where_cond)}"
    else:
        where_clause = ""
    qtext = f"DELETE FROM {table}{where_clause}"
    # print("§§§", qtext)
    query = QSqlQuery()
    if query.exec(qtext):
        return True
    error = query.lastError()
    REPORT("ERROR", error.text())
    return False


"""
# This picks up unique columns, but not unique constraints on multiple columns
def db_unique_fields(table):
    fieldinfo = db_query(f"PRAGMA table_info({table})")
    fields = []
    for uf in db_query(f"PRAGMA index_list({table})"):
        if uf[2] == 1:  # "unique"
            # second element is like f'sqlite_autoindex_{table}_n'
            index = int(uf[1].rsplit('_', 1)[1]) - 1
            fields.append(fieldinfo[index][1])
    return fields
"""

#TODO: Increase flexibility by using (e.g.) JSON?
# Where am I still using this?
def read_pairs(data:str) -> list[tuple[str,str]]:
    """Read a list of (key, value) pairs from the given string.

    Each line of the input supplies one such pair.
    Key and value are separated by ':'.
    This format is used for special database fields which
    contain multiple key-value pairs.
    Values containing multiple lines are made possible by using
    backslash-n for newline characters in the stored string. The
    newlines are recovered by this function.
    """
    pairs = []
    for line in data.splitlines():
        try:
            k, v = line.split(":", 1)
            pairs.append((k.strip(), v.strip().replace("\\n", "\n")))
        except ValueError:
            REPORT("ERROR", T["BAD_KEY_VALUE_LIST"].format(text=data))
    return pairs


def write_pairs(pairs:list[tuple[str,str]]) -> str:
    """Convert a list of (key, value) pairs to a string representation.

    Each pair of the input supplies one line of the string.
    Key and value are separated by ':'.
    This format is used for special database fields which
    contain multiple key-value pairs.
    Values containing multiple lines are made possible by using
    backslash-n for newline characters in the stored string.
    """
    lines = []
    for k, v in pairs:
        if ":" in k or "\n" in k:
            REPORT("ERROR", T["BAD_KEY_IN_KV_LIST"].format(key=k))
            continue
        if "\\n" in v:
            REPORT("ERROR", T["NEWLINE_TAG_IN_KV_LIST"].format(val=v))
            continue
        v1 = v.replace("\n", "\\n")
        lines.append(f'{k}:{v1}')
    return "\n".join(lines)


def write_pairs_dict(pairs:dict[str,str]) -> str:
    """Convert a mapping of (key, value) pairs to a string representation.
    See <write_pairs> for further details.
    """
    #TODO: Note that <write_pairs> can also accept an iterator (though
    # the type definition doesn't show this ...)
    return write_pairs(pairs.items())


#TODO: Is this a sensible approach?
# Would it be better to simply do a copy and remove entries which are
# no longer needed?
def migrate_db(path:str, sql_extra: list[str]):
    """Migrate the current database to the next school year.
    The argument is a list of sql commands to execute after creating the
    new database.
    """
    # Get schema of existing database
    sql_list = [row[4] for row in db_query("SELECT * FROM sqlite_schema")
        if row[4]
    ]
    print("\n SCHEMA:")
    for cmd in sql_list:
        print(" --", cmd)

    print("\nNEW DATABASE ...")
    dp = os.path.join(path, "migrated.sqlite")
    DatabaseShortAccess.new_database(dp, sql_list)
    print("  ... @", dp)

    print("\n ++++++++\n")
    db_query(f"ATTACH '{dp}' AS newdb")
#TODO: Maybe more tables to copy?
    for t in ("CLASSES", "SUBJECTS", "TEACHERS", "COURSES", "BLOLCKS", "LESSONS"):
        print(" ++", t)
        db_query(f"INSERT INTO newdb.{t} SELECT * FROM main.{t}")
    db_query("DETACH newdb")

    db = DatabaseShortAccess(dp, "NEW")
    with db:
        query = QSqlQuery(db.con)
        for cmd in  sql_extra:
            if not query.exec(cmd):
                error = query.lastError()
                REPORT("ERROR", f"SQL query failed: {error.text()}\n  {cmd}")
                assert False, "Failed: extend table"


# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-

# An example of code to create and populate the CLASSES table
def enter_classes():
    con = open_database()
    print("TABLES0:", con.tables())

    query = QSqlQuery()
    query.exec("drop table CLASSES")
    if not query.exec(
        "create table CLASSES(CLASS text primary key,"
        " NAME text unique not null, CLASSROOM text)"
    ):
        error = query.lastError()
        REPORT("ERROR", error.text())

    classes = []
    names = []
    classrooms = []
    for i in range(1, 13):
        k = f"{i:02}G"
        classes.append(k)
        names.append(f"{i}. Großklasse")
        classrooms.append(f"r{k}")
        k = f"{i:02}K"
        classes.append(k)
        names.append(f"{i}. Kleinklasse")
        classrooms.append(f"r{k}")
    classes.append("13")
    names.append("13. Klasse")
    classrooms.append("r13")

    classes.append("--")
    names.append("keine Klasse")
    classrooms.append("")

    query.prepare("insert into CLASSES values (?, ?, ?)")
    query.addBindValue(classes)
    query.addBindValue(names)
    query.addBindValue(classrooms)
    if not query.execBatch():
        error = query.lastError()
        REPORT("ERROR", error.text())
    print("TABLES1:", con.tables())


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    #    enter_classes()

    #db_backup()
    #quit(0)

    l = KeyValueList([("a", 1), ("b", 2), ("c", 3)])
    l.append(("d", 4))
    print("KeyValueList:", l)
    print("   ... map('b'):", l.map("b"))

    open_database()

    """
    pay_factors = {
        r[1]: r[0]
        for r in db_read_fields(
            "PAY_FACTORS",
            ("pay_factor_id", "TAG", "WEIGHT")
        )
    }
    print(pay_factors)

    wls = {}

    for lg_id, w, p in db_read_fields(
        "L_GROUPS2",
        ("lg_id", "workload", "PAY_TAG")
    ):
        print("  --", p)
        try:
            n, t = p.split('*')
        except:
            wi = 0
        else:
            f = pay_factors[t]

            if n == '.':
                ni = -1
            else:
                ni = int(n)

            try:
                wi = wls[w]
            except KeyError:
                wi = db_new_row("PAY_TAGS", pay_factor_id=f, NLESSONS=ni)
# Note that there could be leakage here: if all references to a PAY_TAGS
# entry are deleted, the entry will still remain. So there should probably
# be programmatic intervention when deleting l-g entries.
#xxxxxxxxxxxxxxxxxxx
                wls[w] = wi

        db_update_field("L_GROUPS2", "pay_tag_id", wi, lg_id=lg_id)
    """

    print("\nTEACHERS:")
    for k, v in db_key_value_list(
        "TEACHERS", "TID", "FIRSTNAMES", "SORTNAME"
    ):
        print(f"  {k:6}: {v}")

    print("\nCOURSES:")
    for r in db_read_fields(
        "COURSES", ("course", "CLASS", "GRP", "SUBJECT", "TEACHER")
    )[:10]:
        print("  ", r)

    _sid = "En"
    _tid = "MF"
    print(f"\nCOURSES for {_tid} in {_sid}:")
    print("  ", db_values("COURSES", "CLASS", TEACHER=_tid, SUBJECT=_sid))

    fields, values = db_read_full_table("COURSES", CLASS="10G")
    print("\nCOURSES in 10G:", fields)
    for row in values:
        print("  ", row)

    print("\nSUBJECTS:")
    for row in db_read_fields(
        "SUBJECTS",
        ("SID", "NAME", "SORTING"),
        sort_field="SORTING,NAME"
    ):
        print("  ", row)

# It seems that null entries are read as empty strings "automatically" ...

    quit(0)

    migrate_db(start.year_data_path(Dates.next_year()), [])
