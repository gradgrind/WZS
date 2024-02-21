"""
core/new_db.py - last updated 2024-02-21

Switching to a new database structure (again) ...

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
NEW_DATABASE = "wznew.sqlite"

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

### +++++

import sqlite3
import json

from core.base import (
    DATAPATH,
)

### -----


def make_new_db():
    dbpath = DATAPATH(DATABASE)
    assert os.path.isfile(dbpath)
    # Open databases
    con0 = sqlite3.connect(dbpath)
    newpath = DATAPATH(NEW_DATABASE)
    if os.path.isfile(newpath):
        os.remove(newpath)
    con1 = sqlite3.connect(newpath)
#        con0.row_factory = sqlite3.Row   # for dict-like access
    cur0 = con0.cursor()
    cur1 = con1.cursor()
    cur1.execute(
    """CREATE TABLE NODES (
        id          INTEGER PRIMARY KEY NOT NULL,
        DB_TABLE    TEXT    NOT NULL,
        DATA        TEXT    NOT NULL
    )
    STRICT;"""
    )
    con1.commit()

    cur0.execute(
    """SELECT name FROM sqlite_schema
            WHERE type ='table' AND name NOT LIKE 'sqlite_%';
    """
    )
    # Collect references
    refmap = {}
    tmap = {}
    for tbl in (t[0] for t in cur0.fetchall() if not t[0].startswith("old_")):
        print("§TABLE", tbl)
        cur0.execute(f"PRAGMA foreign_key_list({tbl})")
        refmap[tbl] = []
        tmap[tbl] = []
        for fk in cur0.fetchall():
            print("  --", fk)
            target, field, dest_field = fk[2:5]
            # fk[2]: target table name
            # fk[3]: field in this table
            # fk[4]: target field
            assert dest_field == "id"
            refmap[tbl].append((field, target))
            tmap[tbl].append(target)
    # Order the tables for dependencies
    tables = []
    while tmap:
        _tmap = {}
        for tbl, deps in tmap.items():
            for d in deps:
                if d not in tables:
                    _tmap[tbl] = deps
                    break
            else:
                tables.append(tbl)
        assert len(_tmap) < len(tmap)
        tmap = _tmap
    print("  +++++", tables)
    tmpmap = {}
    for tbl in tables:
        print("§§TABLE", tbl)
        idmap = {}
        tmpmap[tbl] = idmap
        cur0.execute(f"SELECT * from {tbl}")
        fields = [d[0] for d in cur0.description]
        print("==", fields)
        rfields = refmap.get(tbl) or []
        print(">>>", rfields)

        for r in cur0.fetchall():
            #print("  **", r)
            val = {f: r[i] for i, f in enumerate(fields)}
            recid = val.pop("id")
            if tbl == "STUDENTS":
                x = val.pop("__EXTRA__")
                if x:
                    val.update(json.loads(x))
            elif tbl == "CLASSES":
                x = val["DIVISIONS"]
                if x:
                    val["DIVISIONS"] = json.loads(x)
            elif tbl == "GRADES":
                x = val["GRADE_MAP"]
                if x:
                    val["GRADE_MAP"] = json.loads(x)
            elif tbl == "GRADE_FIELDS":
                x = val["DATA"]
                if x:
                    val["DATA"] = json.loads(x)
            elif tbl == "__CONFIG__":
                x = val["DATA"]
                if x and x[0] in ("{", "["):
                    val["DATA"] = json.loads(x)
            # References need to be rewritten
#TODO: Note that this will cause problems anywhere the old id is actually
# used for processing, e.g. as an index.
# Perhaps I should add index fields?
            for field, target in rfields:
                id = val[field]
#TODO: How to handle 0-references?
                if id == 0:
                    pass
                val[field] = tmpmap[target][id]
# Perhaps the reference details should be stored somewhere too?
            if recid == 0:
#TODO: Put these somewhere else? A "NULL_ENTRY" table? Or perhaps in
# The reference table?
                val["_i"] = "0"
            cur1.execute(
                "INSERT INTO NODES(DB_TABLE, DATA) VALUES(?,?)",
                (tbl, to_json(val))
            )
            idmap[recid] = cur1.lastrowid
        con1.commit()
    con1.close()
    con0.close()


def to_json(item):
    return json.dumps(item, ensure_ascii = False, separators = (',', ':'))


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    make_new_db()
