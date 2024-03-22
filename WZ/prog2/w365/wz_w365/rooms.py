"""
w365/wz_w365/rooms.py - last updated 2024-03-22

Manage rooms data.

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
#T = Tr("w365.wz_w365.rooms")

### +++++

from w365.wz_w365.w365base import (
    W365_DB,
    _Room,
    _Shortcut,
    _Name,
    _Id,
    _RoomGroup,
    _ListPosition,
    _capacity,
    LIST_SEP,
    absences,
    categories,
)

### -----

# There are normal rooms and there are room-groups. The latter is a
# collection of normal rooms intended to be used by a "course" which covers
# more than one actual course (I think ...).

def read_rooms(w365_db):
    table = "ROOMS"
    _nodes = []
    _roomgroups = []
    for node in w365_db.scenario[_Room]:
        nid = node[_Shortcut]
        name = node[_Name]
        cap = node.get(_capacity) or ""
        xnode = {"ID": nid, "NAME": name, "CAPACITY": cap}
        rg = node.get(_RoomGroup)
        if rg:
            _roomgroups.append(
                (float(node[_ListPosition]), rg, node[_Id], xnode)
            )
        else:
            _nodes.append((float(node[_ListPosition]), node[_Id], xnode))
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
    # Add "room group" info (one "virtual" room to cover several real
    # rooms, all of which are required).
    w365id_nodes.clear()
    for _, rg, w365id, xnode in sorted(_roomgroups):
        # Get db-keys from w365-ids
        ridlist = [w365_db.id2key[_id] for _id in rg.split(LIST_SEP)]
        i += 1
        xnode["#"] = i
        xnode["ROOM_GROUP"] = ridlist
        w365id_nodes.append((w365id, xnode))
    # Add to database
    w365_db.add_nodes(table, w365id_nodes)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

# Remove existing database file, add rooms from w365.

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

    read_rooms(w365)
