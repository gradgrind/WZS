# This is not really part of WZ. It is just a basis for code to manipulate
# the database during development.

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    basedir = os.path.dirname(this)
    from core.base import setup
    setup(basedir)

from core.base import Tr
T = Tr("core.rooms")

### +++++

from core.basic_data import DB, DB_Table

### -----

'''
class Rooms(DB_Table):
    __slots__ = ()
    _table = "ROOMS"
    order = "RID"
    null_entry = {"RID": "$", "NAME": T("Classroom")}


DB_Table.add_table(Rooms)
'''

db = DB()

'''
#idset = set()
for id, node in db.nodes.items():
    mod = False
    for k in list(node):
        if k.endswith("_id"):
            k2 = f"_{k[:-3]}"
            node.set(**{k2: node[k]})
#            idset.add(k2)
            del node[k]
            mod = True
    if mod:
        print("?", node)
        node.set_modified()
#print("§§§", idset)
'''

'''
    try:
        v = node.pop("_i")
    except KeyError:
        continue
    node.set(**{"#": v})
    print("§", node)
    node.set_modified()
'''

# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

#if __name__ == "__main__":
#    rooms = DB("ROOMS")

#    print("\n§Rooms:")
#    for r in rooms.records():
#        print("  --", r)
