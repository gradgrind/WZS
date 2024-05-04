"""
core/rooms.py - last updated 2024-02-27

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
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(basedir)

from core.base import Tr
T = Tr("core.rooms")

### +++++

from core.basic_data import DB_Table

### -----


class Rooms(DB_Table):
    __slots__ = ()
    _table = "ROOMS"
    order = "RID"
    null_entry = {"RID": "$", "NAME": T("Classroom")}


DB_Table.add_table(Rooms)


class RoomGroups(DB_Table):
    __slots__ = ()
    _table = "TT_ROOM_GROUPS"
    null_entry = {"ROOM_GROUP": "", "DESCRIPTION": "", "_Rooms_": []}


DB_Table.add_table(RoomGroups)


#------------------------------------------------------
#TODO: Are these still needed in this form?


def get_db_rooms(db_rooms: DB_Table, db_room_group_map: DB_Table
) -> tuple[list, list]:
    """Return simplified room and room-group lists from the database.
    These are needed by <print_room_choice> and by the room-choice
    editor.
    As the lists can be invalidated by changes to the database room
    tables, the returned data should not be retained over changes to
    these database tables.
    """
    all_rooms = [(r.id, r.RID, r.NAME) for r in db_rooms.records]
    room_groups = []
#TODO
    for rg, data in db_room_group_map.get_room_lists().items():
        rgdata = data[0]
        room_groups.append((
            rg, rgdata.ROOM_GROUP, rgdata.DESCRIPTION,
            [r[1].id for r in data[1]]
        ))
    return (all_rooms, room_groups)


def print_room_choice(
    room_choice: tuple[list[int], int],
    room_lists: tuple[list, list],
) -> str:
    """Return a displayable (text) version of a room-choice list.
    """
    #print("§print_room_choice:", room_choice)
    room_list, room_groups = room_lists
    rdict = {rid: rtag for rid, rtag, rname in room_list}
    rgdict = {rgid: rgtag for rgid, rgtag, rgname, rlist in room_groups}
    rl = ", ".join(rdict[r] for r in room_choice[0])
    rg = room_choice[1]
    return f"{rl} + {rgdict[rg]}" if rg else rl


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import DB
    rooms = DB("ROOMS")
    print("\n§Rooms:")
    for r in rooms.records():
        print("  --", r)

    rgs = DB("TT_ROOM_GROUPS")
    print("\n§Room groups:")
    for r in rgs.records():
        print("  --", r)
