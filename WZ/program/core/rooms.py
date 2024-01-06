"""
core/rooms.py - last updated 2024-01-06

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
    setup(os.path.join(basedir, 'TESTDATA'))

#from core.base import Tr
#T = Tr("core.rooms")

### +++++

from core.db_access import (
    DB_TABLES,
    db_Table,
    DB_PK,
    DB_FIELD_TEXT,
    DB_FIELD_REFERENCE,
)

### -----

#TODO: Sort on Room_id, coupled with contiguous indexes and
# reallocation of indexes when there are room changes?
# Could then use indexes directly in timetable arrays.

class Rooms(db_Table):
    table = "ROOMS"
    order = "RID"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("RID", unique = True),
                DB_FIELD_TEXT("NAME", unique = True),
            )
            return True
        return False

#    def __init__(self, db: Database):
#        self.init()
#        super().__init__(db)

DB_TABLES[Rooms.table] = Rooms


class RoomGroups(db_Table):
    table = "TT_ROOM_GROUPS"

    @classmethod
    def init(cls):
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("ROOM_GROUP", unique = True),
                DB_FIELD_TEXT("DESCRIPTION", unique = True),
            )

DB_TABLES[RoomGroups.table] = RoomGroups


class RoomGroupMap(db_Table):
    table = "TT_ROOM_GROUP_MAP"

    @classmethod
    def init(cls):
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_REFERENCE("Room_group", target = RoomGroups.table),
                DB_FIELD_REFERENCE("Room", target = Rooms.table),
            )

    def get_room_lists(self) -> dict[str, tuple]:
        """Return information about the room-groups.
        Return a mapping, the key being the RoomGroup id.
        The values are tuples:
            - (a weak ref to) the RoomGroup record
            - a list of tuples:
                - RoomGroupMap_id
                - (a weak ref to) the Room record
        As the result contains record field values extracted from their
        records, it is potentially vulnerable to problems arising
        from changes to individual records. The returned data should thus
        not be retained over changes to these database tables.
        """
        rgmap = self.__room_lists
        if rgmap is not None:
            return rgmap
        rgmap = {}
        for rec in self.records:
            rgi = rec.Room_group.id
            val = (rec.id, rec.Room)
            try:
                rgmap[rgi][1].append(val)
            except KeyError:
                rgmap[rgi] = (rec.Room_group, [val])
        self.__room_lists = rgmap
        return rgmap

    def clear_caches(self):
        # Note that the caches must be cleared if the table is changed.
        self.__room_lists = None

DB_TABLES[RoomGroupMap.table] = RoomGroupMap


def get_db_rooms(db_rooms: db_Table, db_room_group_map: db_Table
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
    from core.basic_data import get_database
    db = get_database()

    #print("?sql:", Rooms.sql_create_table())
    rooms = Rooms(db)

    for rid, index in rooms.id2index.items():
        print(f"\n  {rid}: {index:02d}/{rooms.records[index]}")

    rgm = RoomGroupMap(db)
    for rg_id, rdata in rgm.get_room_lists().items():
        rg, rlist = rdata
        print(f"\n  {rg_id}:: {rg.ROOM_GROUP} // {rg.DESCRIPTION}")
        for r in rlist:
            print(f"   -- ({r[0]}) {r[1]}")
