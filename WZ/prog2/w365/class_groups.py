"""
w365/class_groups.py - last updated 2024-05-04

Manage class, group and student data.


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

#from core.wzbase import Tr
#T = Tr("w365.class_groups")

### +++++

from itertools import product

from w365.w365base import (
    _Shortcut,
    _Name,
    _Id,
    _Group,
    _YearDiv,
    _Groups,
    _Year,
    _Level,
    _Letter,
    _ListPosition,
    _YearDivs,
    _ForceFirstHour,
    _MaxLessonsPerDay,
    _MinLessonsPerDay,
    _NumberOfAfterNoonDays,
    _EpochFactor,
    _Student,
    _Students,
    _PlaceOfBirth,
    _DateOfBirth,
    _StudentId,
    _Gender,
    _Firstnames,
    _First_Name,
    _Home,
    _Postcode,
    _Street,
    _Email,
    _PhoneNumber,
    LIST_SEP,
    absences,
    categories,
    convert_date,
)

#TODO: Somewhere else? Something else?
# It is currently needed as a global in this module.
AG_SEP = "."

### -----

# Should the group date (divisions, grous, students) be stored as part
# of the class data, or as a separate entity? How much is transferable
# from year to year? Perhaps store the groups, with student references
# in a GROUPS table? Even though the groups would only be relevant as
# part of a class, having a separate table for them can help avoiding
# deep JSON trees.

# The data available for a student can vary according to the source.
# How the data is used will determine which fields are necessary (e.g.
# what student data a particular report type needs). Their values are
# strings, but the details may depend on the locality, etc. Dates are
# in ISO-format.
# Certain fields should always be present, though in some cases the
# value may be empty. For the moment I will define the compulsory fields
# to be:
#   ID: unique identifier for the student
#   LASTNAME: the family name, primary sort field
#   FIRSTNAMES: all first names
#   FIRSTNAME: the name by which the student is called, secondary sort field
#   GENDER: whatever is appropriate in the locality (e.g. m/w or m/w/d ...)
#   DATE_BIRTH: the day the student was born
#   BIRTHPLACE: town (perhaps also country)
#   DATE_ENTRY: the day the student was enrolled
#   DATE_EXIT: the day the student left the establishment

def _read_students(w365_db):
    try:
        student_list = w365_db.scenario[_Student]
    except KeyError:
        return
    table = "STUDENTS"
    w365id_nodes = []
    for node in sorted(
        student_list,
#        key = lambda x: float(x[_ListPosition])
        key = lambda x: (x[_Name], x[_First_Name])
    ):
        xnode = {
            "ID": node[_StudentId],
            "LASTNAME": node[_Name],
            "FIRSTNAMES": node[_Firstnames],
            "FIRSTNAME": node[_First_Name],
            "GENDER": node[_Gender],
            "DATE_BIRTH": convert_date(node[_DateOfBirth]),
            "BIRTHPLACE": node[_PlaceOfBirth],
            "DATE_ENTRY": "",   # not available in Waldorf 365!
            "DATE_EXIT": "",   # not available in Waldorf 365!
            # Further fields supplied by Waldorf 365:
            "HOME": node.get(_Home) or "",
            "POSTCODE": node.get(_Postcode) or "",
            "STREET": node.get(_Street) or "",
            "EMAIL": node.get(_Email) or "",
            "PHONE": node.get(_PhoneNumber) or "",
        }
        id365 = node[_Id]
        w365id_nodes.append((id365, xnode))
    # Add students to database
    w365_db.add_nodes(table, w365id_nodes)


# What about groups that are not in divisions? Waldorf 365 supports
# these, they can help when special groups are needed for reports.
# Putting them in a division can, however, aid error checking.
# How these "dummy" groups (and divisions) are handled by the timetabler
# would need to be considered. It might be best to ignore divisions
# if none of the groups are used for real lessons. How would a group
# without a division be handled if it has lessons??


def _read_subgroups(w365_db):
    table = "GROUPS"
    w365id_nodes = []
    id2key = w365_db.id2key
    for node in sorted(
        w365_db.scenario[_Group],
        key = lambda x: float(x[_ListPosition])
    ):
        students = node.get(_Students)
        if students:
            skeys = [id2key[s] for s in students.split(LIST_SEP)]
        else:
            skeys = []
        xnode = {
            # Only the "Shortcut" is used for naming.
            "ID": node[_Shortcut],
            "STUDENTS": skeys,
        }
        id365 = node[_Id]
        w365id_nodes.append((id365, xnode))
    # Add groups to database
    w365_db.add_nodes(table, w365id_nodes)
    # Build a mapping from key to w365id
    w365_db.extra["groupkey_w365id"] = {
        id2key[id365]: id365
        for id365, _ in w365id_nodes
    }
    #print("\n????????????????????????????????")
    #for k, v in w365_db.extra["groupkey_w365id"].items():
    #    print("  --", k, v)


def read_groups(w365_db):
    """Actually this is handling the reading of classes and the
    associated students, groups and divisions
    """
    # First the students (not yet associated with classes)
    _read_students(w365_db)
    # Then the groups (not yet associated with classes)
    _read_subgroups(w365_db)
    table = "CLASSES"
    w365id_nodes = []
    id2key = w365_db.id2key
    id2kdiv = {}
    for node in w365_db.scenario[_YearDiv]: # Waldorf365: "GradePartiton" (sic)
        name = node.get(_Name) or ""
        gklist = [id2key[n] for n in node[_Groups].split(LIST_SEP)]
# Is float(node[_ListPosition]) needed for sorting?
        id2kdiv[node[_Id]] = (name, gklist)
        #print(f" -- {name} = {gklist}")
    group_list = []     # collect group keys for each year
    for node in w365_db.scenario[_Year]:    # Waldorf365: "Grade"
        clevel = node[_Level]
        cletter = node.get(_Letter) or ""
        cltag = f'{clevel}{cletter}'
        students = node.get(_Students)
        if students:
            skeys = [id2key[s] for s in students.split(LIST_SEP)]
        else:
            skeys = []
        xnode = {
            "ID": cltag,
            "SORTING": (int(clevel), cletter),
            "BLOCK_FACTOR": node[_EpochFactor],
            "STUDENTS": skeys,
        }
        # Finish the groups later, when the dbkeys are available ...
        # Collect the necessary info in <g365_info> and <w365id_nodes>.
        yid365 = node[_Id]
        w365id_nodes.append((yid365, xnode))
        divklist = []
        yklist = []
        divs = node.get(_YearDivs)
        if divs:
            for divid in divs.split(LIST_SEP):
                divname, gklist = id2kdiv[divid]
                divklist.append([divname, gklist, []])
                yklist.append(gklist)
        group_list.append((yid365, yklist))
        #print(f'*** {cltag}: {divklist}')
        xnode["PARTITIONS"] = divklist
        gen_class_groups(w365_db.nodes, xnode)
        #print("  *** $GROUP_ATOM_MAP:", xnode["$GROUP_ATOM_MAP"])
        constraints = {
            _f: node[f]
            for f, _f in (
                (_ForceFirstHour, "ForceFirstHour"),
                (_MaxLessonsPerDay, "MaxLessonsPerDay"),
                (_MinLessonsPerDay, "MinLessonsPerDay"),
                (_NumberOfAfterNoonDays, "NumberOfAfterNoonDays"),
            )
        }
        xnode["CONSTRAINTS"] = constraints
        a = absences(w365_db.idmap, node)
        if a:
            xnode["NOT_AVAILABLE"] = a
        c = categories(w365_db.idmap, node)
        if c:
            xnode["EXTRA"] = c
    # Add classes to database
    w365id_nodes.sort(key = lambda x: x[1]["SORTING"])
    w365_db.add_nodes(table, w365id_nodes)
    ## When a group is referenced in Waldorf365 the id can be of a group
    ## or a class. Build a mapping w365id -> (class-key, group-key) for
    ## the classes and groups. The group-key is 0 for the whole class.
    group_map = {}
    w365_db.extra["group_map"] = group_map
    gk2id365 = w365_db.extra["groupkey_w365id"]
    for yid365, yklist in group_list:
        yk = id2key[yid365]
        group_map[yid365] = (yk, 0)     # "whole class" group
        for gkl in yklist:
            for gk in gkl:
                gid = gk2id365[gk]
                group_map[gid] = (yk, gk)


#TODO: The following classes would also be relevant for other data
# sources. Perhaps they should be moved to a different folder?
class AG(frozenset):
    def __repr__(self):
        return f"{{*{','.join(sorted(self))}*}}"

    def __str__(self):
        return AG_SEP.join(sorted(self))


def gen_class_groups(key2node, node):
    """Produce "atomic" groups for the given class partitions.
    This should be rerun whenever any change is made to the partitions –
    including just name changes because the group names are used here.
    <parts> is a list of tuples:
        - name: the partition name (can be empty)
        - list of basic partition group keys
        - list of "compound" groups:
            [compound group key, basic group key, basic group key, ...]
    """
    parts = node["PARTITIONS"]
    if not parts:
        node["$GROUP_ATOM_MAP"] = {"": set()}
        return
    # Check the input
    gset = set()
    divs1 = []
    divs1x = []
    for n, d, dx in parts:
        gs = []
        xg = {}
        divs1.append(gs)
        divs1x.append(xg)
        for gk in d:
            g = key2node[gk]["ID"]
#TODO: use something more helpful than the assertion
            assert g not in gset
            gset.add(g)
            # "Compound" groups are combinations of "basic" groups,
            # as a convenience for input and display of multiple groups
            # within a division (not supported in Waldorf365).
            # Consider a division ["A", "BG", "R"]. There could be
            # courses, say, for combination "A" + "BG". The "compound"
            # group might then be "G", defined as "G=A+BG". Obviously, if
            # this format is used, the symbols "=" and "+" should not be
            # used in group names.
            gs.append(g)   # A "basic" group
        # Deal with compound groups
        for gx in dx:
#TODO: use something more helpful than the assertion
            assert len(gx) > 2
            gc = key2node[gx[0]]["ID"]
            xgl = []
            for gk in gx[1:]:
                g = key2node[gk]["ID"]
#TODO: use something more helpful than the assertion
                assert g in gs
                xgl.append(g)
            xg[gc] = xgl
#TODO: use something more helpful than the assertion
        assert len(gs) > 1
    # Generate "atomic" groups
    g2ag = {}
    aglist = []
    for p in product(*divs1):
        ag = AG(p)
        aglist.append(ag)
        for g in p:
            try:
                g2ag[g].add(ag)
            except KeyError:
                g2ag[g] = {ag}
    for xg in divs1x:
        for g, gl in xg.items():
            ags = set()
            for gg in gl:
                ags.update(g2ag[gg])
            g2ag[g] = ags
    # Add the atomic groups for the whole class
    g2ag[""] = set(aglist)
    node["$GROUP_ATOM_MAP"] = g2ag
