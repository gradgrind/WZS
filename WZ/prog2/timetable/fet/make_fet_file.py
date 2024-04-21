"""
w365/fet/make_fet_file.py - last updated 2024-04-21

Build a fet-file from supplied timetable data.


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

FET_VERSION = "6.18.0"

########################################################################

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(basedir)

#from core.base import Tr
#T = Tr("timetable.fet.make_fet_file")

### +++++

from lib import xmltodict

from timetable.w365.class_groups import AG_SEP
from timetable.fet.fet_support import next_activity_id
from timetable.fet.constraints import get_time_constraints, EXTRA_SUBJECTS

#TODO: This is not fet-specific, all timetable processors would need at
# least some of it. Factor it out.
from timetable.fet.lesson_constraints import SubjectGroupActivities

###-----


def class_groups(node):
    classtag = node["ID"]
    divs = node["DIVISIONS"]
    if not divs:
        return {
            "Name": classtag,
            "Number_of_Students": "0",
            #"Comments": "",
            # The information regarding categories, divisions of each category,
            # and separator is only used in the "divide year automatically by
            # categories dialog" in fet.
            "Number_of_Categories": "0",
            "Separator": AG_SEP,
        }
    cgmap = {
        "Name": classtag,
        "Number_of_Students": "0",
        #"Comments": "",
        # The information regarding categories, divisions of each category,
        # and separator is only used in the "divide year automatically by
        # categories" dialog in fet.
        "Number_of_Categories": "1",
        "Separator": AG_SEP,
    }
    # Add "categories" (atomic groups – not to be confused with the
    # "Categories" in Waldorf365 data)
    g2ag = node["$GROUP_ATOMS"]
    aglist = [str(ag) for ag in g2ag[""]]
    aglist.sort()
    cgmap["Category"] = {
        "Number_of_Divisions": f"{len(aglist)}",
        "Division": aglist,
    }
    # Add groups and subgroups
    groups = []
    cgmap["Group"] = groups
    # If there is only one division, the fet-groups can be the same as
    # fet-subgroups.
    # If there are "compound" groups, these will contain "normal"
    # groups, which then do not need additional fet-group entries.
    #print("\n§CLASS", classtag, "::", [d[1] for d in divs])
    if len(divs) == 1:
        pending = []
        done = set()
        for g in sorted(g2ag):
            if not g:
                continue
            agl = g2ag[g]
            if len(agl) == 1:
                pending.append(g)
            else:
                subgroups = [
                    {
                        "Name": f"{classtag}{AG_SEP}{str(ag)}",
                        "Number_of_Students": "0",
                        #"Comments": "",
                    }
                    for ag in agl
                ]
                groups.append({
                    "Name": f"{classtag}{AG_SEP}{g}",
                    "Number_of_Students": "0",
                    #"Comments": "",
                    "Subgroup": subgroups,
                })
                #print(f">>> {g} -> {agl}")
                done.update(list(ag)[0] for ag in agl)
        for g in pending:
            if g not in done:
                groups.append({
                    "Name": f"{classtag}{AG_SEP}{g}",
                    "Number_of_Students": "0",
                    #"Comments": "",
                })
                #print(f">>> {g}")
    else:
        for g in sorted(g2ag):
            if not g:
                continue
            agl = g2ag[g]
            subgroups = [
                {
                    "Name": f"{classtag}{AG_SEP}{str(ag)}",
                    "Number_of_Students": "0",
                    #"Comments": "",
                }
                for ag in agl
            ]
            groups.append({
                "Name": f"{classtag}{AG_SEP}{g}",
                "Number_of_Students": "0",
                #"Comments": "",
                "Subgroup": subgroups,
            })
            #print(f">>> {g} -> {agl}")
    return cgmap


#=======================================================================


def get_days(data, fetout):
    days = []
    fetlist = []
    for node in data.tables["DAYS"]:
        d = node["ID"]
        days.append(d)
        fetlist.append({"Name": d})
    fetout["Days_List"] = {
        "Number_of_Days":   f"{len(fetlist)}",
        "Day": fetlist,
    }
    return days


def get_periods(data, fetout):
    periods = []
    fetlist = []
    for node in data.tables["PERIODS"]:
        p = node["ID"]
        periods.append(p)
        fetlist.append({"Name": p})
    fetout["Hours_List"] = {
        "Number_of_Hours":   f"{len(fetlist)}",
        "Hour": fetlist,
    }
    return periods


def get_teachers(data, fetout):
    fetlist = [{
        "Name": node["ID"],
        "Target_Number_of_Hours": "0",
        "Qualified_Subjects": None,
        "Comments": f'{node["FIRSTNAMES"]} {node["LASTNAME"]}'
    } for node in data.tables["TEACHERS"]]
    fetout["Teachers_List"] = {"Teacher": fetlist}


def get_subjects(data, fetout):
    fetlist = EXTRA_SUBJECTS()
#    sids = set()
    for node in data.tables["SUBJECTS"]:
        sid = node["ID"]
        fetlist.append({"Name": sid, "Comments": node["NAME"]})
#        sids.add(sid)
    fetout["Subjects_List"] = {"Subject": fetlist}
#    data.sids = sids


def get_groups(data, fetout):
    fetout["Students_List"] = {"Year": [
        class_groups(node) for node in data.tables["CLASSES"]
    ]}


def get_rooms(data, fetout):
    fetlist = []
    rconstraints = {}
    roomgroups = []
    for node in data.tables["ROOMS"]:
        #print("ROOM:", node)
        rid = node["ID"]
        rname = node["NAME"]
        rglist = node.get("ROOM_GROUP")
        if rglist:
            roomgroups.append((rid, rname, rglist))
        else:
            fetlist.append({
                "Name": rid,
                "Building": "",
                "Capacity": node["CAPACITY"] or "30000",
                "Virtual": "false",
                "Comments": rname,
            })
    # Make virtual rooms with one-room elements for the room-groups
    for rid, rname, rglist in roomgroups:
        roomlist = [
            {
                "Number_of_Real_Rooms": "1",
                "Real_Room": data.key2node[roomkey]["ID"],
            }
            for roomkey in rglist
        ]
        fetlist.append({
            "Name": rid,
            "Building": "",
            "Capacity": "30000",
            "Virtual": "true",
            "Number_of_Sets_of_Real_Rooms": str(len(roomlist)),
            "Set_of_Real_Rooms": roomlist,
            "Comments": rname,
        })
    fetout["Rooms_List"] = {"Room": fetlist}


def get_activities(data, fetout):
    fetlist = []
    next_activity_id(reset = True)
    subject_activities = SubjectGroupActivities(data.full_atomic_groups)
    key2node = data.key2node
    for node in data.tables["COURSES"]:
        sbj = key2node[node["SUBJECT"]]["ID"]
        tlist = node.get("TEACHERS") or []
        tidlist = [key2node[t]["ID"] for t in tlist]
        gidlist = []
        for cx, g in node["GROUPS"]:
            if g:
                gidlist.append(f'{key2node[cx]["ID"]}{AG_SEP}{g}')
            else:
                gidlist.append(key2node[cx]["ID"])
        #rlist = node.get("ROOM_WISH") or []
        #ridlist = [key2node[r]["ID"] for r in rlist]
        ## Generate the activity or activities
        try:
            durations = node["LESSONS"]
            total_duration = sum(durations)
            # sum also works with an empty list (-> 0)
        except KeyError:
#?
            continue
#TODO
# How would a "course" with no lessons look? (A bodge to cater for
# extra workloads/payments/reports)

        activity_list = []
        node["$ACTIVITIES"] = activity_list
        id0 = str(next_activity_id())
        aid_list = [id0]
        activity = {
            "Id": id0,
            "Teacher": tidlist,
            "Subject": sbj,
            "Students": gidlist,
            "Active": "true",
            "Total_Duration": str(total_duration),
            "Activity_Group_Id": id0 if len(durations) > 1 else "0",
        }
        activity["Comments"] = node["$W365ID"]
        for i, ll in enumerate(durations):
            if i > 0:
                activity = activity.copy()
                aid = str(next_activity_id())
                activity["Id"] = aid
                aid_list.append(aid)
            activity["Duration"] = str(ll)
            fetlist.append(activity)
            activity_list.append(activity)
        subject_activities.add_activities(sbj, gidlist, aid_list)
    data.set_subject_activities(subject_activities)

# Defining a set of lessons as an "Activity_Group" / subactivities
# is a way of grouping activities which are split into a number
# of lessons (such as English in group 10A for three lessons
# per week). It is not of much significance for my usage of fet,
# but it might be useful to have this coupling within the fet gui.
# Uncoupled activitities are given Activity_Group_Id = '0',
# a set of coupled activities is given as Activity_Group_Id the
# (activity) Id of the first member of the set. The other
# members of the set get the immediately following Id numbers,
# but the same Activity_Group_Id. The parameter Total_Duration
# is the sum of the Duration parameters of all the members.

    fetout["Activities_List"] = {"Activity": fetlist}


#TODO: Is this needed only for fet, or elsewhere, too?
# Possibly move it somewhere else, to be shared.
def get_full_atomic_groups(data):
    """Return a mapping of all groups (with class prefix) to
    their "atomic" groups (also with class prefix).
    """
    atomic_groups = {}
    for node in data.tables["CLASSES"]:
        #print(" ***", node)
        clid = node["ID"]
        group_atoms = node["$GROUP_ATOMS"]
        ag_kag = {
            ag: f"{clid}{AG_SEP}{ag}"
            for ag in group_atoms[""]
        }
        for g, ags in group_atoms.items():
            kg = f"{clid}{AG_SEP}{g}" if g else clid
            atomic_groups[kg] = {ag_kag[ag] for ag in ags} or {clid}
    return atomic_groups


#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


def build_fet_file(data):
    """Given the necessary information, build an input file for "fet".

    Note that where the order of the input data is important, it should
    already be sorted before passing it in here.
    """
    fetout = {
        "@version": FET_VERSION,
        "Mode": "Official",
        "Institution_Name": data.config["SCHOOL"],
#TODO: Redo this without the w365 dependency:
        "Comments": data.scenario["$$SCENARIO"]["Id"],
    }
    fetbase = {"fet": fetout}

    days = get_days(data, fetout)
    periods = get_periods(data, fetout)
    get_teachers(data, fetout)
    get_subjects(data, fetout)
    get_groups(data, fetout)
    fetout["Buildings_List"] = ""
    get_rooms(data, fetout)

#TODO?
    # A mapping class-group -> full atomic groups is needed for constraints
    data.set_atomic_groups(get_full_atomic_groups(data))

    get_activities(data, fetout)
    get_time_constraints(data, fetout, days, periods)

#TODO: ### Space constraints
    scmap = {
        "ConstraintBasicCompulsorySpace": {
            "Weight_Percentage": "100",
            "Active": "true",
            "Comments": None,
        }
    }
    fetout["Space_Constraints_List"] = scmap

    return xmltodict.unparse(fetbase, pretty=True, indent="  ")


#-----------------------------------------------------------------------


if __name__ == "__main__":
    from core.base import DATAPATH

    dbpath = DATAPATH("db365.sqlite", "w365_data")
    #w365path = DATAPATH("test.w365", "w365_data")
    #w365path = DATAPATH("fwsb.w365", "w365_data")
    #w365path = DATAPATH("fms.w365", "w365_data")
    w365path = DATAPATH("fms_xep.w365", "w365_data")
    print("DATABASE FILE:", dbpath)
    print("W365 FILE:", w365path)

    from timetable.w365.read_w365 import read_w365
    w365db = read_w365(w365path)

    fetxml = build_fet_file(w365db)

    #print("\n§XML:", fetxml)
    #quit(1)

    outfile = f'{os.path.basename(w365path).rsplit(".", 1)[0]}.fet'
    outpath = os.path.join(os.path.dirname(w365path), outfile)
    with open(outpath, "w", encoding = "utf-8") as fh:
        fh.write(fetxml)
    print("\n  ==>", outpath)
