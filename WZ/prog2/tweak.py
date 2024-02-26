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
#import core.classes
#print("\n§§§ CLASSES:")

print("\n§§§ COURSE_TEACHERS:")
ct_ids = db.node_tables["COURSE_TEACHERS"]
for id in ct_ids:
    node = db.nodes[id]
    print("  --", node)

print("\n§§§ COURSE_GROUPS:")
cg_ids = db.node_tables["COURSE_GROUPS"]
for id in cg_ids:
    node = db.nodes[id]
    print("  --", node)

print("\n§§§ COURSES:")
course_ids = db.node_tables["COURSES"]
for id in course_ids:
    node = db.nodes[id]
    print("  --", node)

'''
import core.classes
# Build STUDENT_GROUPS table entries
newtable = "STUDENT_GROUPS"
db.node_tables[newtable] = []
classes = DB("CLASSES")
for rec in classes.records():
    #print("\n======================================================")
    #print("\n?DIVISIONS:", rec)
    divdata = classes.group_data(rec._id)
    #print("\n?group_info:")
    g2id = {}
    for g, info in divdata["group_info"].items():
        div = info.group_index[0]
        data = {
            "_Class": rec._id, "NAME": g if div else "", "DIV": div
        }
        pos = info.group_index[1]
        if pos < 0:
            data["POS"] = f":{-pos:02}"
            data[f"_{newtable}_"] = [
                g2id[gg]
                for gg in info.compound_components
            ]
        else:
            data["POS"] = f"{pos:02}"
        id = db.add_node(newtable, **data)
        print(id, data)
        g2id[g] = id


#TODO: Add "atomic_group_bitmap", "atomic_group_set"? These are derivable
# and so they can be generated on demand. On the other hand, this data will
# rarely change, so it might make sense to have it in the database.
'''


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
