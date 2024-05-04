"""
core/wzbase.py

Last updated:  2024-05-04

Basic configuration and structural stuff.

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
    # Enable package import if running module directly
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
else:
    appdir = sys.path[0]
basedir = os.path.dirname(appdir)


def APPDATAPATH(path):
    """Return a path within the school-data folder.
    <path> is a '/'-separated path relative to this folder.
    """
    return os.path.join(basedir, "program-data", *path.split("/"))

### +++++

from configparser import ConfigParser
import json
import sqlite3
from typing import NamedTuple

__REPORT = None
__DATA: str = None              # Base folder for school data
SYSTEM: dict[str, str] = None   # System configuration information
CONFIG_TABLE = "__CONFIG__"


class DB_Error(Exception):
    """An exception class for errors occurring during database access."""

### -----

__TRANSLATIONS = ConfigParser(interpolation = None)
__TRANSLATIONS.read(APPDATAPATH("i18n.ini"), encoding = "utf-8")


def Tr(module_key):
    tk = __TRANSLATIONS[module_key]

    def __translator(_key, **kargs):
        return tk[_key].replace("¶", "\n").format(**kargs)

    return __translator

T = Tr("core.wzbase")


def set_reporter(function):
    global __REPORT
    __REPORT = function


def __report(mtype, text):
    """The default reporting function prints to stdout.
    It's effect can be overridden later by calling <set_reporter>.
    """
    if __REPORT:
        __REPORT(mtype, text)
    else:
        print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print(f"{mtype}: {text}", flush=True)
        print("-----------------------------------------------------\n")


def REPORT_CRITICAL(text):
    __report("CRITICAL", text)
    quit(1)


def REPORT_ERROR(text):
    __report("ERROR", text)


def REPORT_WARNING(text):
    __report("WARNING", text)


def REPORT_INFO(text):
    __report("INFO", text)


def REPORT_OUT(text):
    __report("OUT", text)


def REPORT_DEBUG(text):
    if DEBUG:
        __report("DEBUG", text)

# TODO: configuration/settings file?
# posix: os.path.expanduser('~/.config/WZ')
# win: os.path.expanduser('~\\AppData\\Local\\Programs\\WZ\\config')
# Could use the "winpath" package, but it seems unnecessary!
# Can perhaps also install to the WZ folder on windows?
# Perhaps there can also be a launcher there (see python)?
# On Linux install to .local/(bin, lib, share)? or to ~/bin/WZ?


def setup(basedir, year = None, debug = False):
    """Initialize data paths, etc.
    <basedir> is the full path to the folder containing the year-data
    folders.
    <datadir> is the folder to be selected (containing the school data
    for the current year).
    """
    global __DATA, SYSTEM, DEBUG
    DEBUG = debug
    if year:
        __DATA = year_data_path(year, basedir = basedir)
    else:
        __DATA = os.path.join(basedir, "TESTDATA")
    # Get the system configuration information
    SYSTEM = read_config_file(os.path.join(basedir, "CONFIG"))


def read_config_file(cpath: str) -> dict[str, str]:
    config = {}
    with open(cpath, "r", encoding = "utf-8") as fh:
        for line in fh.read().splitlines():
            line = line.strip()
            if line and line[0] != ";":
                try:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if k:
                        config[k] = v.strip()
                    else:
                        raise ValueError
                except ValueError:
                    REPORT_CRITICAL(
                        T("INVALID_CONFIG_LINE", line = line, path = cpath))
    return config


class NODE(NamedTuple):
    table: str
    nid: int
    data: dict[str, str | int | list | dict]

    def __getitem__(self, field: str):
        return self.data[field]

    def __setitem__(self, field: str, value: str | int | list | dict):
        self.data[field] = value


class WZDatabase:
    """A basic handler for an SQLite database, where only the table
    "NODES" is significant. The data is divided into wz-tables (field
    "DB_TABLE"), and the value (field "DATA") is JSON.
    """
    __slots__ = (
        "path",
        "conn",
        "nodes",
        "node_tables",
        "config",
        "config1"
    )

    def __init__(self, year = None, memory = False):
        """If no year is given, the path will be the default accessible
        via <DATAPATH>.
        """
        if year:
            data = year_data_path(year, basedir = basedir)
        else:
            data = DATAPATH("")
        self.config = read_config_file(os.path.join(data, "CONFIG"))
        self.path = os.path.join(data, SYSTEM["DATABASE"])
        if memory:
            dbexists = False
            # Retain the "connection":
            self.conn = sqlite3.connect(":memory:")
        else:
            dbexists = os.path.isfile(self.path)
            # Retain the "connection":
            self.conn = sqlite3.connect(self.path)
        # Read all "nodes"
        self.node_tables = {}
        self.nodes = {}
        if dbexists:
            for _id, table, data in self.select("* from NODES"):
                self.new_node(table, _id, json.loads(data))
            try:
                c = self.node_tables[CONFIG_TABLE]
            except KeyError:
                # As the entry is created with a new database, this
                # should never happen ...
                _id = self.insert(CONFIG_TABLE, [{}])[0]
                self.new_node(CONFIG_TABLE, _id, {})
            else:
                if len(c) > 1:
                    REPORT_ERROR(T("MULTIPLE_CONFIGS", path = self.path))
                _id = self.nodes[c[0]]
        else:
            if not memory:
                REPORT_WARNING(T("NEW_DATABASE", path = self.path))
            self.query("""
                CREATE TABLE NODES (
                    id       INTEGER PRIMARY KEY    NOT NULL,
                    DB_TABLE TEXT    NOT NULL,
                    DATA     TEXT    NOT NULL
                )
                STRICT;
            """)
            _id = self.insert(CONFIG_TABLE, [{}])[0]
            self.new_node(CONFIG_TABLE, _id, {})
        self.config1 = self.nodes[_id]

    def query(self, sql: str, data: tuple | list = None) -> sqlite3.Cursor:
        #print("§query:", sql, "\n  --", data)
        cur = self.conn.cursor()
        try:
            cur.execute(sql, data or ())
        except sqlite3.Error as e:
            cur.close()
            raise DB_Error(f"{type(e).__name__}: {e}")
        return cur

    def select(self, xsql: str) -> list[tuple]:
        cur = self.query(f"select {xsql}")
        rows = cur.fetchall()
        cur.close()
        return rows

    def commit(self):
        self.conn.commit()

    def transaction(self, sql: str, data: tuple | list = None) -> id:
        """Run a "query", close cursor, commit.
        Return the "lastrowid", the id-field of the changed record, which
        is useful for new records.
        """
        cur = self.query(sql, data)
        cur.close()
        _id = cur.lastrowid
        self.commit()
        return _id

    def new_node(self, table, _id, datamap):
        self.nodes[_id] = NODE(table, _id, datamap)
        try:
            self.node_tables[table].append(_id)
        except KeyError:
            self.node_tables[table] = [_id]

    def insert(
        self,
        table: str,
        values: list[dict[str, str | int | list | dict]]
    ) -> list[int]:
        """Insert new entries into the "NODES" table, given the "DB_TABLE"
        name and a list of mappings, each of which will be stored as JSON.
        """
        sql = f"insert into NODES (DB_TABLE, DATA) values (?, ?)"
        cur = self.conn.cursor()
        ids = []
        try:
            for data in values:
                cur.execute(sql, (table, to_json(data)))
                _id = cur.lastrowid
                ids.append((_id, data))
        except sqlite3.Error as e:
            cur.close()
            self.rollback()
            raise DB_Error(f"{type(e).__name__}: {e}")
        cur.close()
        self.commit()
        idlist = []
        for _id, data in ids:
            self.new_node(table, _id, data)
            idlist.append(_id)
        return idlist

    def delete(self, table: str, rowid: int):
        """Remove the row with the given id from the given table.
        """
        self.transaction(
            f"delete from {table} where rowid=?",
            (rowid,)
        )
        self.node_tables[table].remove(rowid)
        del self.nodes[rowid]

    def update(self, rowid: int, data: dict[str, str | int | list | dict]):
        """Update the DATA field of the given record, converting the
        supplied mapping to JSON.
        Access is via the rowid (only). This is accessed using the
        alias "rowid", so the outward-facing name of this column
        is not important.
        """
        self.transaction(
            f"update NODES set DATA = ? where rowid = ?",
            (to_json(data), rowid)
        )
        dmap = self.nodes[rowid].data
        dmap.clear()
        dmap.update(data)

    def save(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        self.query(f"vacuum main into '{self.path}'")
        REPORT_WARNING(T("NEW_DATABASE", path = self.path))


def to_json(item: dict[str, str | int | list | dict]):
    """Convert the given item to a json object.
    Any first-level (!) keys starting with "$" will be omitted.
    """
    val = {
        _k: _v
        for _k, _v in item.items()
        if _k[0] != "$"
    }
    return json.dumps(val, ensure_ascii = False, separators = (',', ':'))


def year_data_path(year, path = "", basedir = None):
    """Return the directory (full path) containing the data for the
    given year.
    """
    return os.path.join(
        basedir or os.path.dirname(__DATA),
        f"DATA-{year}",
        *path.split("/")
    )


def DATAPATH(path, base= ""):
    """Return a path within the school-data folder.
    <path> is a '/'-separated path relative to this folder.
    <base> is an optional alternative, '/'-separated base folder
    within the data folder.
    """
    return os.path.join(__DATA, *base.split("/"), *path.split("/"))


def RESOURCEPATH(path):
    """Return a path within the resources folder.
    <path> is a '/'-separated path relative to this folder.
    """
    return os.path.join(__DATA, "RESOURCES", *path.split("/"))


def pr_group(k, g):
    if g:
        return f"{k}.{g}"
    return k


def pr_course(db, xnode):
    glist = ",".join(
        pr_group(db.nodes[k]["ID"], g)
        for k, g in xnode["GROUPS"]
    )
    sbj = db.nodes[xnode["SUBJECT"]]["ID"] or "{}"
    tlist = ",".join(
        db.nodes[t]["ID"]
        for t in xnode["TEACHERS"]
    )
    return f'{glist}-{sbj}-{tlist or "{}"}'


# TODO?:
'''
import tarfile

# tarfile doesn't have the encoding problems some
# filenames have with zipfile.
def archive_testdata():
    # The filter is perhaps a nice idea, but I suspect it is not really of
    # much practical use. If an archive is unpacked by a normal user, its
    # contents will be owned by that user anyway.
    def owner(tf0):
        tf0.uid = 0
        tf0.gid = 0
        tf0.uname = "root"
        tf0.gname = "root"
        return tf0

    with tarfile.open("testdata.tar.gz", "w:gz") as tf:
        for root, directories, files in os.walk("TESTDATA"):
            if os.path.basename(root) == "tmp":
                continue
            for filename in files:
                #tf.add(os.path.join(root, filename), filter = owner)
                tf.add(os.path.join(root, filename))


# To read just one file
# tx = tf.extractfile('TESTDATA/CONFIG')
# tx.read() -> <bytes>
'''


if __name__ == "__main__":
    setup(basedir, debug = True)

    _db = WZDatabase()
    print("\n?1:", _db.config)

