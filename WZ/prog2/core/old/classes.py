"""
core/classes.py - last updated 2024-02-28

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
    setup(basedir)

from core.base import Tr
T = Tr("core.classes")

### +++++

from typing import NamedTuple
from itertools import product

from core.base import REPORT_WARNING
from core.basic_data import DB_Table, DB, to_json

GROUP_ALL = "*"
#NO_CLASS = "--"


class GroupInfo(NamedTuple):
    group_index: tuple[int, str]
    compound_components: [list[str]]
    atomic_group_bitmap: int
    atomic_group_set: int


class DIV_Error(Exception):
    """An exception class for errors occurring while reading
    class divisions.
    """

#TODO: Add configuration option and code to support schools with
# no class divisions? Or is support already adequate?


def format_student_group(sgid: int) -> str:
    node = DB().nodes[sgid]
    return format_class_group(node.Class.CLASS, node.NAME)


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
        return f"{c}{DB().CONFIG.CLASS_GROUP_SEP}{g}"
    return f"({c})"


#TODO???
def class_group_split(
    class_group: str, whole_class: str = None
) -> tuple[str, str]:
    """Split a full group descriptor (class.group, etc.) into class and
    group.
    If <whole_class> is supplied, it will be used instead of <GROUP_ALL>.
    """
    REPORT_WARNING("<class_group_split()> needs updating?")
    if class_group.startswith("("):
        assert class_group.endswith(")")
        return (class_group.strip("()"), "")
    try:
        class_group, g = class_group.split(DB().CONFIG.CLASS_GROUP_SEP, 1)
    except ValueError:
        g = GROUP_ALL if whole_class is None else whole_class
    return (class_group, g)


#TODO???
def class_group_split_with_id(class_group: str) -> tuple[int, str]:
    """Split a full group descriptor (class.group, etc.) into class and
    group. The class is returned as its database id.
    """
    REPORT_WARNING("<class_group_split_with_id()> needs updating?")
    c, g = class_group_split(class_group)
    return (DB("CLASSES").class2id(c), g)

### -----


class Classes(DB_Table):
    __slots__ = ("class2id",)
    _table = "CLASSES"
    order = "CLASS"
    null_entry = {
        "CLASS": "--",
        "YEAR": "",
        "NAME": "keine Klasse",
        "_Classroom": 0,
    }

    def setup(self):
        # Set up a class -> id map
        self.class2id = {
            self.db.nodes[id].CLASS: id
            for id in self.db.node_tables[self._table]
        }


DB_Table.add_table(Classes)


class StudentGroups(DB_Table):
    __slots__ = ()
    _table = "STUDENT_GROUPS"
    null_entry = {"_Class": 0, "NAME": "", "DIV": -1, "POS": "00"}


DB_Table.add_table(StudentGroups)


def group_data(class_id: int):
    nodes = DB().nodes
    divs = []
    gmap = {}
    for r in DB("STUDENT_GROUPS").records():
        if r._Class == class_id:
            tag = r.NAME
            gmap[tag] = r._id
            d = r.DIV
            if d < 1:
                continue
            while len(divs) < d:
                divs.append([])
            val = [
                r.POS,
                tag,
                [nodes[id].NAME for id in r.get("_STUDENT_GROUPS_") or []]
            ]
            divs[d - 1].append(val)
    for dl in divs:
        dl.sort()
    return gmap, divs


def class_divisions(division_list: list[list[list]]):
    """Read the division/group info for a class, build the
    necessary data-structures.
    """
    group_info = {}     # map group to an info structure
    raw_divs = []
#           gx2g = {}   # map group index, (idiv, ig), to group name
    idiv = 0    # division index, starts at 1 for "real" divisions
    for div in division_list:
        idiv += 1
        g0list = []
        for pos, g, cmp in div:
            # Check that g is unique (in all divisions)
            if check_group_name(g):
                if g in group_info:
                    raise DIV_Error(T(
                        "REPEATED_GROUP", div = div, group = g
                    ))
            else:
                raise DIV_Error(T(
                    "INVALID_GROUP", div = div, group = g
                ))
            gclist = []
            if cmp:
                # compound group
                for gc in cmp:
                    if gc in g0list:
                        if gc in gclist:
                            raise DIV_Error(T(
                                "REPEATED_COMPOUND_GROUP",
                                div = div,
                                group = gc
                            ))
                        gclist.append(gc)
                    else:
                        raise DIV_Error(T(
                            "INVALID_COMPOUND_GROUP",
                            div = div,
                            group = gc
                        ))
                if len(gclist) < 2:
                    raise DIV_Error(T(
                        "TOO_FEW_PRIMARIES", div = div, group = g
                    ))
            else:
                # simple group
                g0list.append(g)
            group_info[g] = [(idiv, pos), gclist]
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
    group_info[GROUP_ALL] = [(0, "00"), []]
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
    return divdata


#import re
def check_group_name(g):
#    return bool(re.match("^[A-Za-z][A-Za-z0-9/-]*$", g))
    return g.isalnum()


#TODO: deprecated?
def make_divisions(group_info: dict[str, GroupInfo]) -> str:
    """Make a "canonical" JSON string from the given group-info.
    """
    REPORT_WARNING("<make_divisions()> deprecated?")
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
    div_list = []
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
        div_list.append(simples + compounds)
    return to_json(div_list) if div_list else ''


#TODO: Handle TT_CLASSES table

# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    classes = DB("CLASSES")

    for rec in classes.records():
        print("\n  --", rec)
        gmap, divs = group_data(rec._id)
        print(" ++ gmap:", gmap)
        print(" .. divs:", divs)

        divdata = class_divisions(divs)
        print(" >>>>>>>>>>>>>>>>>>>>>>")
        for k, v in divdata.items():
            print(" $$$", k, v)

    quit(1)

    for rec in classes.records():
        print("\n======================================================")
        print("\n?DIVISIONS:", rec)
        divdata = classes.group_data(rec._id)

        print("\n?raw_divisions:", divdata["raw_divisions"])
        print("\n?atomic_groups:", divdata["atomic_groups"])
        print("\n?agbitmap2g:", divdata["agbitmap2g"])
        print("\n?group_info:")
        for g, info in divdata["group_info"].items():
            print(f"   {g}: {info}")

        print(
            "\n?Canonical DIVISIONS:",
            repr(make_divisions(divdata["group_info"]))
        )

    quit(2)

    import fastjsonschema

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
    # JSON schema for mappings str -> str, the keys are restricted
    SIMPLE_SCHEMA = {
        "type": "object",
        "patternProperties":
            {"^[A-Za-z_][A-Za-z0-9_]*$": {"type": "string"}},
        #"additionalProperties": {"type": "string"},
        "additionalProperties": False
    }
    print("$$$1", fastjsonschema.validate(
        SIMPLE_SCHEMA,
        {'H': 'hello', "_ab3": "2"}
    ))

    print("???1", fastjsonschema.validate({'type': 'string'}, 'hello'))
    print("???2", fastjsonschema.validate(DIVISIONS_SCHEMA, [['hello']]))
    print(
        "???3", fastjsonschema.validate(
            DIVISIONS_SCHEMA,
            [['A', 'BG', 'R', 'G=A+BG', 'B=BG+R'], ['X', 'Y']]
        )
    )
#    print(
#        "???4", fastjsonschema.validate(
#            DIVISIONS_SCHEMA,
#            [['A', 'BG', 'R', 'G=A+BG', 'B=BG']]
#        )
#    )
