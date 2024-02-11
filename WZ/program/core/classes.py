"""
core/classes.py - last updated 2024-02-11

Manage class data.

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

from core.base import Tr
T = Tr("core.classes")

### +++++

from typing import NamedTuple, Optional
from itertools import product

from core.base import REPORT_CRITICAL
from core.db_access import (
    DB_TABLES,
    db_Table,
    DB_PK,
    DB_FIELD_TEXT,
    DB_FIELD_JSON,
    DB_FIELD_REFERENCE,
)
from core.basic_data import get_database, CONFIG
from core.rooms import Rooms

GROUP_ALL = "*"
#NO_CLASS = "--"

class GroupInfo(NamedTuple):
    group_index: tuple[int, int]
    compound_components: Optional[list[str]]
    atomic_group_bitmap: int
    atomic_group_set: int

class DIV_Error(Exception):
    """An exception class for errors occurring while reading
    class divisions.
    """

#TODO: Add configuration option and code to support schools with
# no class divisions? Or is support already adequate?

def format_class_group(c: str, g: str, whole_class: str = None) -> str:
    """Make a full class-group descriptor from the class and the possibly
    null ("") group.
    If <whole_class> is supplied, it will be used instead of <GROUP_ALL>.
    """
    if whole_class is None:
        whole_class = GROUP_ALL
    if g == whole_class:
        return c
    if g:
        return f"{c}{CONFIG.CLASS_GROUP_SEP}{g}"
    return f"({c})"
#+
def class_group_split(class_group: str, whole_class: str = None
) -> tuple[str, str]:
    """Split a full group descriptor (class.group, etc.) into class and
    group.
    If <whole_class> is supplied, it will be used instead of <GROUP_ALL>.
    """
    if class_group.startswith("("):
        assert class_group.endswith(")")
        return (class_group.strip("()"), "")
    try:
        class_group, g = class_group.split(CONFIG.CLASS_GROUP_SEP, 1)
    except ValueError:
        g = GROUP_ALL if whole_class is None else whole_class
    return (class_group, g)
#+
def class_group_split_with_id(class_group: str) -> tuple[int, str]:
    """Split a full group descriptor (class.group, etc.) into class and
    group. The class is returned as its database id.
    """
    c, g = class_group_split(class_group)
    classes = get_database().table("CLASSES")
    for rec in classes.records:
        if rec.CLASS == c:
            return (rec.id, g)
    REPORT_CRITICAL(
        "Bug: classes::class_group_split_with_id:"
        f" group '{class_group}' is unknown"
    )

### -----


#CG_REGEX = "[A-Za-z0-9_/-]"
#GROUP_REGEX = f"^({CG_REGEX}+)(=({CG_REGEX}+[+])+({CG_REGEX}+))?$"
DIVISIONS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "array",
        "items": {
            "type": "string",
#TODO: without pattern (here)? ... it must still be parsed and that
# would repeat the checking
#            "pattern": GROUP_REGEX
        }
    }
}

#import re
#rx = f"^({GROUP_REGEX}+)(=({GROUP_REGEX}+[+])+({GROUP_REGEX}+))?$"
#print("§re:", re.match(rx, "G=A+B").groups())
#print("§re:", re.match(rx, "G0").groups())
#print("§re:", re.match(rx, "09G").groups())
#print("§re:", re.match(rx, "G=A").groups())


class Classes(db_Table):
    table = "CLASSES"
    order = "CLASS"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("CLASS", unique = True),
                DB_FIELD_TEXT("YEAR"),
                DB_FIELD_TEXT("NAME", unique = True),
                DB_FIELD_REFERENCE("Classroom", target = Rooms.table),
                DB_FIELD_JSON(
                    "DIVISIONS",
                    schema = DIVISIONS_SCHEMA,
                    empty = [],
                ),
            )
            return True
        return False

    def class_list(self, skip_null: bool = True):
        """Return an ordered list of classes.
        """
        classes = []
        for data in self.records:
            c = data.id
            if c != 0 or not skip_null:
                classes.append((c, data.CLASS, data.NAME))
        return classes

    def clear_caches(self):
        # Note that the caches must be cleared if the table is changed.
        self.__divisions = {}

    def group_data(self, class_id: int):
        try:
            divdata = self.__divisions[class_id]
        except KeyError:
            record = self[class_id]
            div0 = record.DIVISIONS

            ### Read the division/group info for a class, build the
            ### necessary data-structures.

            group_info = {} # map group to an info structure
            raw_divs = []
#           gx2g = {}   # map group index, (idiv, ig), to group name
            idiv = 0    # division index, starts at 1 for "real" divisions
            for div in div0:
                idiv += 1
                g0list = []
                ig = 0      # simple group index (>=0)
                igg = 0     # compound group index (<0)
                for g in div:
                    # Check that g is unique (in all divisions)
                    try:
                        gg, cstr = g.split('=')
                    except ValueError:
                        # simple group
                        if check_group_name(g):
                            if g in group_info:
                                raise DIV_Error(T("REPEATED_GROUP",
                                    div = div, group = g
                                ))
                            g0list.append(g)
                            gx = (idiv, ig)
                            ig += 1
                            group_info[g] = [gx, None]
#                           gx2g[gx] = g
                        else:
                            raise DIV_Error(T("INVALID_GROUP", 
                                div = div, group = g
                            ))
                    else:
                        # compound group
                        if check_group_name(gg):
                            if gg in group_info:
                                raise DIV_Error(T("REPEATED_GROUP",
                                    div = div, group = gg
                                ))
                        else:
                            raise DIV_Error(T("INVALID_GROUP",
                                div = div, group = gg
                            ))
                        gclist = []
                        for gc in cstr.split('+'):
                            if gc in g0list:
                                if gc in gclist:
                                    raise DIV_Error(
                                        T("REPEATED_COMPOUND_GROUP",
                                            div = div, group = gc
                                        )
                                    )
                                gclist.append(gc)
                            else:
                                raise DIV_Error(
                                    T("INVALID_COMPOUND_GROUP",
                                        div = div, group = gc
                                    )
                                )
                        if len(gclist) < 2:
                            raise DIV_Error(T("TOO_FEW_PRIMARIES",
                                div = div, group = g
                            ))
                        igg -= 1
                        group_info[gg] = [(idiv, igg), gclist]
                        # Note that with this indexing the compound groups
                        # are indexed in reverse order of appearance.
                if len(g0list) < 2:
                    raise DIV_Error(T("TOO_FEW_GROUPS", div = div))
                raw_divs.append(g0list)
            aglist = list(product(*raw_divs)) if raw_divs else []
            ## Construct a mapping, group -> {constituent atomic groups}.
            # Store the set both as a bitmap value and as a set of group tags.
            # First just the primary groups.
            g2agset = {}
            g2agbitmap = {}
            for g in group_info:
                g2agset[g] = set()
                g2agbitmap[g] = 0
            # Special handling of a class with no divisions:
            if not aglist:
                # Add the whole-class atomic group
                g2agset[GROUP_ALL] = {0}
                g2agbitmap[GROUP_ALL] = 0
                aglist.append((GROUP_ALL,))
            aghash = 1
            for i, ag in enumerate(aglist):
#               agtext = ".".join(ag)
#               aghash2agtext[aghash] = agtext
#               agtext2aghash[agtext] = aghash
                for g in ag:
                    g2agset[g].add(i)
                    g2agbitmap[g] |= aghash
                aghash <<= 1
            # Add the compound groups
            for gg, ginfo in group_info.items():
                gclist = ginfo[1]
                if gclist:
                    agbits = 0
                    agset = set()
                    for g in gclist:
                        agbits |= g2agbitmap[g]
                        agset |= g2agset[g]
                    g2agset[gg] = agset
                    g2agbitmap[gg] = agbits
            # Add the whole-class group
            group_info[GROUP_ALL] = [(0, 0), None]
            g2agset[GROUP_ALL] = {i for i in range(len(aglist))}
            g2agbitmap[GROUP_ALL] = aghash - 1
            # Put the contents of the two sets into group_info and build
            # a reverse mapping, aghash-set -> group
            agbitmap2g = {}
            gdata = {}
            for g, agbits in g2agbitmap.items():
                gdata[g] = GroupInfo(*group_info[g], agbits, g2agset[g])
                agbitmap2g[agbits] = g

            #print("\n  ------------------------------------------------")
            #print("\n§raw_divs:", raw_divs)
            ##print("\n§gx2g:", gx2g)
            #print("\n§group_info:", group_info)
            #print("\n§aglist:", aglist)
            ##print("\n§aghash2agtext:", aghash2agtext)
            ##print("\n§agtext2aghash:", agtext2aghash)
            #print("\n§g2agset:", g2agset)
            ##print("\n§g2agbitmap:", g2agbitmap)
            #print("\n§agbitmap2g:", agbitmap2g)
            divdata = {
                "raw_divisions": raw_divs,
                "atomic_groups": aglist,
                "group_info": gdata,
                "agbitmap2g": agbitmap2g,
            }
            self.__divisions[class_id] = divdata
        return divdata

DB_TABLES[Classes.table] = Classes


#import re
def check_group_name(g):
#    return bool(re.match("^[A-Za-z][A-Za-z0-9/-]*$", g))
    return g.isalnum()


def make_divisions(group_info: dict[str, GroupInfo]) -> str:
    """Make a "canonical" JSON string from the given group-info.
    """
    divmap = {}
    for g, info in group_info.items():
        idiv, index = info.group_index
        if idiv == 0:
            continue    # whole class, here not relevant
        val = (index, g, info.compound_components)
        try:
            divmap[idiv].append(val)
        except KeyError:
            divmap[idiv] = [val]

    divs = []
    for idiv in sorted(divmap):
        glist = divmap[idiv]
        glist.sort()
        compounds = []
        simples = []
        for _, g, components in glist:
            if components:
                # compound group
                compounds.append(f"{g}={'+'.join(components)}")
            else:
                # simple group
                simples.append(g)
        compounds.reverse()
        d = ','.join(f'"{g}"' for g in simples + compounds)
        divs.append(f'[{d}]')
    return f"[{','.join(d for d in divs)}]" if divs else ''


#TODO: Handle TT_CLASSES table

# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":

    import fastjsonschema

    # JSON schema for mappings str -> str, the keys are restricted
    SIMPLE_SCHEMA = {
        "type": "object",
        "patternProperties":
            { "^[A-Za-z_][A-Za-z0-9_]*$": {"type": "string"}},
        #"additionalProperties": {"type": "string"},
        "additionalProperties": False
    }
    print("$$$1", fastjsonschema.validate(
        SIMPLE_SCHEMA,
        {'H': 'hello', "_ab3": "2"}
    ))

    print("???1", fastjsonschema.validate({'type': 'string'}, 'hello'))
    print("???2", fastjsonschema.validate(DIVISIONS_SCHEMA, [['hello']]))
    print("???3", fastjsonschema.validate(DIVISIONS_SCHEMA,
            [['A', 'BG', 'R', 'G=A+BG', 'B=BG+R'], ['X', 'Y']]
        )
    )
#    print("???4", fastjsonschema.validate(DIVISIONS_SCHEMA,
#            [['A', 'BG', 'R', 'G=A+BG', 'B=BG']]
#        )
#    )

#    quit(1)

    db = get_database()

    #print("\n?sql:", Classes.sql_create_table())
    classes = Classes(db)

    for cid, index in classes.id2index.items():
        print(f"\n  {cid}: {index:02d}/{classes.records[index]}")

    print("\n?DB_TABLES:", DB_TABLES)

    print("\n?Classes.field2type:", db.table("CLASSES").field2type)
    print("\n?Rooms.field2type:", db.table("ROOMS").field2type)

    print("\n**************************************\n class_list():")
    for data in classes.class_list():
        print("  --", data)

    print("\n======================================================\n")

    for rec in classes.records:
        print("\n?DIVISIONS:", rec)
        divdata = classes.group_data(rec.id)

        print("\n?raw_divisions:", divdata["raw_divisions"])
        print("\n?atomic_groups:", divdata["atomic_groups"])
        print("\n?agbitmap2g:", divdata["agbitmap2g"])
        print("\n?group_info:")
        for g, info in divdata["group_info"].items():
            print(f"   {g}: {info}")

        print("\n?Canonical DIVISIONS:",
            repr(make_divisions(divdata["group_info"]))
        )
