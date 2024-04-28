"""
timetable/w365/class_groups.py - last updated 2024-04-28

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

#from core.base import Tr
#T = Tr("timetable.w365.class_groups")

### +++++

from itertools import product

from timetable.w365.w365base import (
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
    table = "STUDENTS"
    w365id_nodes = []
    for node in sorted(
        w365_db.scenario[_Student],
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
    # Add students to database
    w365_db.add_nodes(table, w365id_nodes)


def read_groups(w365_db):
    """Actually this is handling the reading of classes and the
    associated students, groups and divisions
    """
    # First the students (not yet associated with classes)
    _read_students(w365_db)
    # Then the groups (not yet associated with classes)
    _read_subgroups(w365_db)

    ## When a group is referenced in Waldorf365 the id can be of a group
    ## or a class. Build a mapping w365id -> (class-key, group-str) for
    ## the classes and groups.

    table = "CLASSES"
    w365id_nodes = []
    id2key = w365_db.id2key


#TODO: Move to indexing for groups ... what effect will that have on
# modules that use this?

    id2div = {}
    #id_div = []
    for node in w365_db.scenario[_YearDiv]: # Waldorf365: "GradePartiton" (sic)
        name = node.get(_Name) or ""
        gklist = [id2key[n] for n in node[_Groups].split(LIST_SEP)]
# Is float(node[_ListPosition]) needed?
        id2div[node[_Id]] = (name, gklist)
        print(f" -- {name} = {gklist}")
#?
        #id_div.append((float(node[_ListPosition]), node[_Id], name, gklist))
    #print("\n&&&1:", id_div)
    #id_div.sort()
    #print("&&&2:", id_div)


#old:

    id2gtag = {
        node[_Id]: (float(node[_ListPosition]), node[_Shortcut])
        for node in w365_db.scenario[_Group]
    }
    id2div = {}


    for node in w365_db.scenario[_YearDiv]: # Waldorf365: "GradePartiton" (sic)
        name = node.get(_Name) or ""
        gidlist = node[_Groups].split(LIST_SEP)
        iglist = [(*id2gtag[w365id], w365id) for w365id in gidlist]
        iglist = [(g, g365) for lp, g, g365 in sorted(iglist)]
        id2div[node[_Id]] = (float(node[_ListPosition]), name, iglist)
        #print(f" -- {name} = {iglist}")


    g365_info = {}  # collect group references for each class


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
        divlist = []
        y2glist = []
        g365_info[yid365] = y2glist     # collect group references
        divs = node.get(_YearDivs)
        if divs:
            for divid in divs.split(LIST_SEP):
                divlp, divname, iglist = id2div[divid]
                glist = []
                for gx in iglist:
                    glist.append(gx[0])
                    y2glist.append(gx)
                divlist.append((divlp, divname, glist))
            divlist.sort()
            divlist = [[n, gl] for lp, n, gl in divlist]
        print(f'+++ {cltag}: {divlist}')
        xnode["DIVISIONS"] = divlist
        xnode["$GROUP_ATOMS"] = make_class_groups(divlist)
        #print("  *** $GROUP_ATOMS:", xnode["$GROUP_ATOMS"])
        constraints = {
            f: node[f]
            for f in (
                _ForceFirstHour,
                _MaxLessonsPerDay,
                _MinLessonsPerDay,
                _NumberOfAfterNoonDays,
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
    # Construct a look-up mapping for class/group (w365id) -> wz-form
    group_map = {}
    for y365, gxlist in g365_info.items():
        yid = w365_db.id2key[y365]
        group_map[y365] = (yid, "")     # "whole class" group
        for g, g365 in gxlist:
            group_map[g365] = (yid, g)
#?
    w365_db.group_map = group_map
    #print("§group_map:", group_map)


class AG(frozenset):
    def __repr__(self):
        return f"{{*{','.join(sorted(self))}*}}"

    def __str__(self):
        return AG_SEP.join(sorted(self))


def make_class_groups(divs):
    if not divs:
        return {"": set()}
    # Check the input
    gset = set()
    divs1 = []
    divs1x = []
    for n, d in divs:

#TODO-- (just testing)
#        if "BG" in d:
#            d.append("G=A+BG")
#            d.append("B=BG+R")

        gs = []
        xg = {}
        divs1.append(gs)
        divs1x.append(xg)
        for g in d:
            assert g not in gset
            gset.add(g)
            # "Compound" groups are combinations of "normal" groups,
            # as a convenience for input and display of multiple groups
            # within a division (not supported in Waldorf365).
            # Consider a division ["A", "BG", "R"]. There could be
            # courses, say, for combination "A" + "BG". The "compound"
            # group might then be "G", defined as "G=A+BG". Obviously
            # the symbols "=" and "+" should not be used in group names.
            try:
                g, subs = g.split("=", 1)
            except ValueError:
                gs.append(g)   # A "normal" group
            else:
                # A "compound" group
                xl = []
                xg[g] = xl
                for s in subs.split("+"):
                    assert s not in xl
                    xl.append(s)
        for g, sl in xg.items():
            assert len(sl) > 1
            for s in sl:
                assert s in gs
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
    return g2ag
