"""
w365/wz_w365/teachers.py - last updated 2024-03-21

Manage teachers data.

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

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(basedir)

#from core.base import Tr
#T = Tr("w365.wz_w365.teachers")

### +++++

from w365.wz_w365.w365base import (
    W365_DB,
    _Teacher,
    _Shortcut,
    _Name,
    _Firstname,
    _Id,
    _MaxDays,
    _MaxGapsPerDay,
    _MaxLessonsPerDay,
    _MinLessonsPerDay,
    _NumberOfAfterNoonDays,
    _ListPosition,
    absences,
    categories,
)

### -----


def read_teachers(w365_db):
    table = "TEACHERS"
    _nodes = []
    for node in w365_db.scenario[_Teacher]:
        _id = node[_Shortcut]
        name = node[_Name]
        xnode = {
            "ID": _id,
            "LASTNAME": node[_Name],
            "FIRSTNAMES": node[_Firstname],
            #"SEX": int(node[_Gender]),  # 0: male, 1: female
            # There is also other personal information ...
        }
        _nodes.append((float(node[_ListPosition]), node[_Id], xnode))
        constraints = {
            f: node[f]
            for f in (
                _MaxDays,
                _MaxLessonsPerDay,
                _MaxGapsPerDay,    # gaps
                _MinLessonsPerDay,
                _NumberOfAfterNoonDays,
            )
        }
        xnode["$$CONSTRAINTS"] = constraints
        a = absences(w365_db.idmap, node)
        if a:
            xnode["NOT_AVAILABLE"] = a
        c = categories(w365_db.idmap, node)
        if c:
            xnode["$$EXTRA"] = c
    w365id_nodes = []
    i = 0
    for _, _id, xnode in sorted(_nodes):
        i += 1
        xnode["#"] = i
        w365id_nodes.append((_id, xnode))
    # Add to database
    w365_db.add_nodes(table, w365id_nodes)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

# Remove existing database file, add teachers from w365.

if __name__ == "__main__":
    from core.base import DATAPATH
    from w365.wz_w365.w365base import read_active_scenario

    dbpath = DATAPATH("db365.sqlite", "w365_data")
    w365path = DATAPATH("test.w365", "w365_data")
    print("DATABASE FILE:", dbpath)
    print("W365 FILE:", w365path)
    try:
        os.remove(dbpath)
    except FileNotFoundError:
        pass

    filedata = read_active_scenario(w365path)
    w365 = W365_DB(dbpath, filedata)

    read_teachers(w365)
