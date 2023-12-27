"""
core/db_access.py

Last updated:  2023-12-27

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

DATABASE = "wzx_2.sqlite"

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

from core.base import TRANSLATIONS
T = TRANSLATIONS("core.db_access")

### +++++

from typing import Any

import sqlite3
import re
import json
#TODO: Am I using json schemas anywhere???
import fastjsonschema
import weakref

from core.base import (
    REPORT_ERROR,
    REPORT_CRITICAL,
    REPORT_WARNING,
)

class DB_Error(Exception):
    """An exception class for errors occurring during database access."""

__DB = None     # the current database
CONFIG = {}     # the configuration mapping of the current database

DB_TABLES = {}  # map the table names to their handler classes

### -----


class Database:
    def __init__(self, dbpath):
        if not os.path.isfile(dbpath):
            REPORT_WARNING(f"TODO: No database at:\n  {dbpath}")
        self.path = dbpath
        con = sqlite3.connect(dbpath)
#        con.row_factory = sqlite3.Row   # for dict-like access
        ## Check foreign key support
        cursor = con.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        con.commit()
        cursor.execute("PRAGMA foreign_keys")
        if not cursor.fetchone()[0] == 1:
            REPORT_CRITICAL("TODO: Foreign keys not supported:\n  {dbpath}")
        # Retain the "connection":
        self.conn = con
        self.tables = {}

    def query(self, sql: str, data: dict|tuple = None) -> sqlite3.Cursor:
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

    def update(self,
        table: str,
        rowid: int,
        field: str,
        value: int|str
    ):
        """Update a single field of a single record of a table.
        Access is via the rowid (only). This is accessed using the
        alias "rowid", so the outward-facing name of this column
        is not important.
        """
        cur = self.query(
            f"update {table} set {field} = ? where rowid = ?",
            (value, rowid)
        )
        cur.close()
        self.commit()

    def update_fields(self,
        table: str,
        rowid: int,
        fields: list[tuple[str, int|str]],
    ):
        """Update multiple fields of a single record of a table.
        Access is via the rowid (only). This is accessed using the
        alias "rowid", so the outward-facing name of this column
        is not important.
        """
        flist, vlist = [], []
        for f, v in fields:
            flist.append(f"{f} = ?")
            vlist.append(v)
        vlist.append(rowid)
        cur = self.query(
            f"update {table} set {', '.join(flist)} where rowid = ?",
            vlist
        )
        cur.close()
        self.commit()

    def insert(self, table: str, fields: list[str], values: list[str|int]
    ) -> int:
        """Insert a new row containing the given data into the given table.
        """
        flist = ", ".join(fields)
        slots = ", ".join('?' for f in fields)
        if len(values) != len(fields):
            REPORT_CRITICAL("Bug: mismatched arguments to Database.insert")
        cur = self.query(
            f"insert into {table} ({flist}) values ({slots})",
            values
        )
        id = cur.lastrowid
        cur.close()
        self.commit()
        return id

    def delete(self, table: str, rowid: int):
        """Remove the row with the given id from the given table.
        """
        cur = self.query(
            f"delete from {table} where rowid=?",
            (rowid,)
        )
        cur.close()
        self.commit()

    def table(self, name: str):# -> db_Table:
        try:
            t = self.tables[name]
        except KeyError:
            t = DB_TABLES[name](self)
            self.tables[name] = t
        return t


class DB_FIELD:
    """Base class for database field types.
    """
    foreign_key = False

    def __init__(self, field: str, dbtype: str, unique: bool):
        self.field = field  # field in the memory data-structure
        # Foreign keys have a different field name in the database:
        self.field0 = (field + "_id") if self.foreign_key else field
        self.dbtype = dbtype    # data-type for database creation
        self.unique = unique    # unique attribute on database field

    def validate(self, db: Database, val: str|int) -> tuple[Any, str]:
        """Validate the value from the database field.
        Input: the database field value.
        Return: checked value or None, error-message or ""
        """
        return val, ""


class db_Table:
    """Base class for a database table.
    This class should not be instantiated directly as various essential
    parameters are supplied as attributes of the sub-class!

    The database table records are available as a list via the
    attribute "records".
    There is also a mapping (attribute "id2index") from the record's
    id-field to the list index corresponding to that record.
    """
    table: str = None
    order: str = None
    fields: list[DB_FIELD] = None
    field2type: dict[str, DB_FIELD] = None
    # For each table which is referred to by others, collect those
    # referring tables:
    depends: dict[str, set[str]] = {}

    @classmethod
    def init_fields(cls, *fields):
        cls.fields = fields
        cls.field2type = {}
        for f in fields:
            cls.field2type[f.field] = f
            try:
                cls.depends[f.target].add(cls.table)
            except KeyError:
                cls.depends[f.target] = {cls.table}
            except AttributeError:
                pass
#TODO?: As Python dicts are ordered, the "fields" attribute is not
# really necessary. However, it does not add a lot of weight.

    @classmethod
    def sql_create_table(cls):
        """Return the sql command which would create the database table.
        The "init" method (of the subclass) must have been called
        previously, otherwise there will be no fields registered.
        """
        # Don't call "init" here because that will interfere with the
        # automatic creation of the table ... should it not exist already.
        # See "__init__".
        #cls.init() # set up fields, method supplied by sub-class
        if cls.fields:
            fields = ", ".join(
                f"{f.field0} {f.dbtype}"
                f"{' UNIQUE' if f.unique else ''} NOT NULL"
                for f in cls.fields
            )
            return f"create table if not exists {cls.table} ({fields}) strict;"
        REPORT_CRITICAL(f"TODO: Table {cls.table} not initialized")

    def reset(self):
        """Unload the table and all those that depend on it.
        """
        #print(
        #    "§reset table:", self.table,
        #    "depends:", self.depends.get(self.table)
        #)
        for d in self.depends.get(self.table) or []:
            try:
                t = self.db.tables[d]
            except KeyError:
                continue
            t.reset()
        del self.db.tables[self.table]
        #print("§   -->", self.db.tables)

    def __init__(self, db: Database):
        self.db = weakref.proxy(db)
        if self.init(): # set up fields, method supplied by sub-class
            try:
                # Ensure that table exists
                cur = db.query(self.sql_create_table())
            finally:
                cur.close()
            db.commit()
        try:
            self.clear_caches()
        except AttributeError:
            pass
        order = f" order by {self.order}" if self.order else ""
        #print("§INIT", self.table, order)
        flist = ",".join(f.field0 for f in self.fields)
        sq = f"{flist} from {self.table}{order}"
        records = []
        self.records = records
        id2index = {}
        self.id2index = id2index
#        rowname = f"{self.table}_Row"
        for row in self.db.select(sq):
            fmap = db_TableRow(self)
            for i, val in enumerate(row):
                ftype = self.fields[i]
                v, e = ftype.validate(self.db, val)
                if e:
                    REPORT_ERROR(
                        f"TODO: DB-Error in {self.table}"
                        f"[{row[0]}.{ftype.field0}]:\n  {e}"
                    )
                setattr(fmap, ftype.field, v)
            id2index[row[0]] = len(records)
            records.append(fmap)
            #print("§row:", fmap)

    def __getitem__(self, rowid: int):
        """Return the record with the given id.
        """
        return self.records[self.id2index[rowid]]

    def update_cell(self, rowid: int, field: str, value: str|int) -> bool:
        """Update a table cell. The value should already be preprocessed
        (if that is necessary), so that it can be directly written to the
        database.
        Also the memory-based data structure will be updated.
        Return <True> if successful.
        """
        ## Check validity of value
        # Get the field type
        ftype = self.field2type[field]
        # Check validity of value
        v, e = ftype.validate(self.db, value)
        if e:
            REPORT_ERROR(T["UPDATE_VALIDATION_FAILED"].format(
                table = self.table, field = field, rowid = rowid, e = e
            ))
            return False
        ## Save to database.
        #print("§self.db.update:", self.table, rowid, ftype.field0, value)
        self.db.update(self.table, rowid, ftype.field0, value)
        ## Set the memory cell
        #print("§setattr:", ftype.field, v, "\n  ++", self.id2index)
        setattr(self[rowid], ftype.field, v)
        return True

    def update_json_cell(
        self,
        rowid: int,
        field: str,
        **jsonfields: dict[str, Any]
    ):
        """Update a table cell containing json.
        Writing the empty string to a json-field will remove the
        corresponding key, if it is present.
        Also the memory-based data structure will be updated.
        """
        ftype = self.field2type[field]
        if not isinstance(ftype, DB_FIELD_JSON):
            REPORT_CRITICAL(
                "Bug: <update_json_cell> called on non-json field:"
                f" {self.table}.{field}"
            )
        record = self[rowid]
        jsonmap = getattr(record, ftype.field)
        newmap = {}
        for k, v in jsonmap.items():
            try:
                v1 = jsonfields.pop(k)
                if v1 != "":
                    newmap[k] = v1
            except KeyError:
                newmap[k] = v
        # New json-fields
        newmap.update(jsonfields)
        # Prepare text value
        value = json.dumps(
            newmap,
            ensure_ascii = False,
            separators = (',', ':')
        )
        self.db.update(self.table, rowid, ftype.field0, value)
        ## Set the memory cell
        setattr(record, ftype.field, newmap)


    def update_cells(self, rowid: int, **fields: dict[str, str|int]) -> bool:
        """Update fields of a table record. The values should already be
        preprocessed (if that is necessary), so that they can be directly
        written to the database.
        Also the memory-based data structure will be updated.
        Return <True> if successful.
        """
        ## Check validity of values
        cells_db = []
        cells_mem = []
        for field, value in fields.items():
            # Get the field type
            ftype = self.field2type[field]
            # Check validity of value
            v, e = ftype.validate(self.db, value)
            if e:
                REPORT_ERROR(T["UPDATE_VALIDATION_FAILED"].format(
                    table = self.table, field = field, rowid = rowid, e = e
                ))
                return False
            cells_db.append((ftype.field0, value))
            cells_mem.append((ftype.field, v))
        ## Save to database.
        self.db.update_fields(self.table, rowid, cells_db)
        ## Set the memory cells
        rec = self[rowid]
        for f, v in cells_mem:
            setattr(rec, f, v)
        return True

    def add_records(self, records: list[dict[str, str|int]]) -> list[int]:
        """Insert new records into the table.
        As "None" is not acceptable here, all fields must be provided
        except for the row-id.
        For the special case where a specific row-id should be used,
        the parameter <id> should be set.
        Return a list containing the rowids of the inserted records.
        """
        ids = []
        for rec in records:
            flist, vlist = [], []
            ## Check validity of values
            for field, ftype in self.field2type.items():
                try:
                    value = rec[field]
                except KeyError:
                    if field == "id":
                        continue
                    REPORT_CRITICAL(
                        "Bug, while inserting new record into table"
                        f" {self.table}:\n  No value for field '{field}'"
                    )
                # Check validity of value
                v, e = ftype.validate(self.db, value)
                if e:
                    REPORT_ERROR(T["INSERT_VALIDATION_FAILED"].format(
                        table = self.table, field = field, e = e
                    ))
                    break
                flist.append(ftype.field0)
                vlist.append(value)
            else:
                ids.append(self.db.insert(self.table, flist, vlist))
        self.reset()
        return ids

    def delete_records(self, ids: list[int]):
        for id in ids:
            try:
                _ = self[id]
            except KeyError:
                REPORT_CRITICAL(
                    "Bug: Attempt to delete non-existent"
                    f" record with id = {id} in table {self.table}"
                )
            self.db.delete(self.table, id)
        self.reset()


class db_TableRow:
    def __init__(self, table: db_Table):
        self._table: db_Table = weakref.proxy(table)

    def __repr__(self):
        items = (
            f"{k}={repr(self.__dict__[k])}" for k in self.__dict__
            if k[0] != "_"
        )
        return f"{self._table.table}_Row({', '.join(items)})"

    def _todict(self):
        d = {}
        for k, v in self.__dict__.items():
            if k[0] != "_":
                try:
                    d[k] = v.id
                except AttributeError:
                    d[k] = v
        return d

    def _write(self, field: str, value: Any) -> bool:
        #print("§_write:", self._table.table, self.id, field, value)
        return self._table.update_cell(self.id, field, value)


class DB_FIELD_INTEGER(DB_FIELD):
    def __init__(self,
        field: str,
        unique: bool = False,
        min: int = None,
        max: int = None
    ):
        super().__init__(field, "INTEGER", unique)
        self.min = min
        self.max = max

    def validate(self, db: Database, val: int) -> tuple[int, str]:
        """Validate the value from the database field.
        Input: the database field value.
        Return a tuple:
            * checked value structure or 0,
            * error-message or ""
        """
        if not isinstance(val, int):
            return 0, "TODO: Not a number"
        if (
            (self.min is not None and val < self.min)
            or (self.max is not None and val > self.max)
        ):
            return 0, "TODO: Out of range"
        return val, ""


class DB_PK(DB_FIELD):
    def __init__(self,
        field: str = "id",
        unique: bool = False,
    ):
        super().__init__(field, "INTEGER PRIMARY KEY", unique)

    def validate(self, db: Database, val: int) -> tuple[int, str]:
        """Validate the value from the database field.
        Input: the database field value.
        Return a tuple:
            * checked value structure or 0,
            * error-message or ""
        """
        if not isinstance(val, int):
            return -1, "TODO: Not a number"
        if val < 0:
            return -1, "TODO: Out of range"
        return val, ""


class DB_FIELD_REFERENCE(DB_FIELD):
    foreign_key = True

    def __init__(self,
        field: str,
        target: str,
        unique: bool = False,
    ):
        dbtype = (
            f"INTEGER REFERENCES {target} (id)"
            f" ON DELETE RESTRICT ON UPDATE RESTRICT"
        )
        super().__init__(field, dbtype, unique)
        self.target = target

    def validate(self, db: Database, val: int) -> tuple[Any, str]:
        if not isinstance(val, int):
            return None, "TODO: Not an integer"
        target_table = db.table(self.target)
        rowdata = target_table[val]
#TODO: Error handling?
#TODO: A special update function is probably needed.
# I need to write the id to the db table, not the pointer, or whatever.
# But the memory structure needs the pointer.

        ref = weakref.proxy(rowdata)
        return ref, ""


class DB_FIELD_TEXT(DB_FIELD):
    def __init__(self,
        field: str,
        unique: bool = False,
        pattern: str = None,
        default: str = "",
    ):
        super().__init__(field, "TEXT", unique)
        self.pattern = pattern
        self.default = default

    def validate(self, db: Database, text:str) -> tuple[str, str]:
        """Validate the value from the database field.
        Input: the database field value.
        Return a tuple:
            * checked text structure or "",
            * error-message or ""
        """
        if not isinstance(text, str):
            return self.default, "TODO: Not a string"
        if self.pattern and not re.match(self.pattern, text):
            return (
                self.default,
                f"TODO: Doesn't match pattern '{self.pattern}'"
            )
        return text, ""


class DB_FIELD_JSON(DB_FIELD):
    """Very similar to DB_FIELD_TEXT, but validation is as JSON with an
    optional schema.
    """
    def __init__(self,
        field: str,
        unique: bool = False,
        schema: Any = None,
        empty: Any = None,
    ):
        super().__init__(field, "TEXT", unique)
        if schema:
            self.schema = fastjsonschema.compile(schema)
        else:
            self.schema = None
        self.empty = empty

    def validate(self, db: Database, text:str) -> tuple[Any, str]:
        """Validate the value from the database field, transform it into
        the corresponding json-structure.
        Input: the database field value.
        Return a tuple:
            * checked json structure or self.empty,
            * error-message or ""
        """
        if not isinstance(text, str):
            return (
                {} if self.empty is None else self.empty,
                "TODO: Not a string"
            )
        if text:
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                return (
                    {} if self.empty is None else self.empty,
                    f"TODO: Invalid JSON: '{text}'"
                )
            if self.schema:
                try:
                    self.schema(obj)
                except fastjsonschema.JsonSchemaException as e:
                    return (
                        {} if self.empty is None else self.empty,
                        f"TODO: Doesn't match schema:\n  {e.message}"
                    )
            return obj, ""
        return {} if self.empty is None else self.empty, ""


class DB_FIELD_FIX(DB_FIELD):
    """Very similar to DB_FIELD_TEXT, but validation is as a decimal
    number.
    """
    def __init__(self,
        field: str,
        unique: bool = False,
        min: float = None,
        max: float = None
    ):
        super().__init__(field, "TEXT", unique)
        self.min = min
        self.max = max

    def validate(self, db: Database, text:str) -> tuple[float, str]:
        """Validate the value from the database field, transform it into
        the corresponding "float".
        Input: the database field value.
        Return a tuple:
            * checked float or 0.0
            * error-message or ""
        """
        if not isinstance(text, str):
            return 0.0, "TODO: Not a string"
        if text:
            try:
                val = float(text.replace(',', '.'))
            except ValueError:
                return 0.0, f"TODO: Invalid float: '{text}'"
            if (
                (self.min is not None and val < self.min)
                or (self.max is not None and val > self.max)
            ):
                return 0.0, "TODO: Out of range"
            return val, ""
        return 0.0, ""
