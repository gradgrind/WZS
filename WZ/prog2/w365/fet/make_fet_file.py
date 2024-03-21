"""
w365/fet/make_fet_file.py - last updated 2024-03-21

Build a fet-file from the timetable data in the database.


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
#T = Tr("w365.fet.make_fet_file")

### +++++

import xmltodict

'''
from w365.fet.fet_support import next_activity_id, AG_SEP
from w365.fet.constraints_subject_separation import (
    SubjectGroupActivities,
)
'''
from w365.fet.constraints import get_time_constraints, EXTRA_SUBJECTS
from w365.wz_w365.class_groups import AG_SEP

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
    if len(divs) == 1:
        pending = []
        done = set()
        for g in sorted(g2ag):
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


def get_days(db, fetout):
    fetlist = [{"Name": node["ID"]} for node in db.tables["DAYS"]]
    fetout["Days_List"] = {
        "Number_of_Days":   f"{len(fetlist)}",
        "Day": fetlist,
    }
    #return fetlist


def get_periods(db, fetout):
    fetlist = [{"Name": node["ID"]} for node in db.tables["PERIODS"]]
    fetout["Hours_List"] = {
        "Number_of_Hours":   f"{len(fetlist)}",
        "Hour": fetlist,
    }
    #return fetlist


def get_teachers(db, fetout):
    fetlist = [{
        "Name": node["ID"],
        "Target_Number_of_Hours": "0",
        "Qualified_Subjects": None,
        "Comments": f'{node["FIRSTNAMES"]} {node["LASTNAME"]}'
    } for node in db.tables["TEACHERS"]]
    fetout["Teachers_List"] = {"Teacher": fetlist}
    #return fetlist


def get_subjects(db, fetout):
    fetlist = EXTRA_SUBJECTS()
    sids = set()
    for node in db.tables["SUBJECTS"]:
        sid = node["ID"]
        fetlist.append({"Name": sid, "Comments": node["NAME"]})
        sids.add(sid)
    fetout["Subjects_List"] = {"Subject": fetlist}
    db.sids = sids
    #return fetlist


def get_groups(db, fetout):
    ylist = []  # Collect class data for fet
    for node in db.tables["CLASSES"]:
        print(" ***", node)
        ylist.append(class_groups(node))
    fetout["Students_List"] = {"Year": ylist}
    #return ylist


def get_rooms(idmap, fetout, scenario):
    id2room = {}
    fetlist = []
    rconstraints = {}
    roomgroups = []
    for node in scenario[_Room]:
        rid = node[_Shortcut]
        rname = node[_Name]
        id2room[node[_Id]] = (rid, rname)
        rg = node.get(_RoomGroup)
        if rg:
            roomgroups.append((rid, rname, rg))
        else:
            fetlist.append({
                "Name": rid,
                "Building": "",
                "Capacity": node.get(_capacity) or "30000",
                "Virtual": "false",
                "Comments": rname,
            })
        rconstraints[rid] = {
            _Absences: absences(idmap, node),
            _Categories: categories(idmap, node)
        }
    # Make virtual rooms with one-room elements for the room-groups
    for rid, rname, rg in roomgroups:
        ridlist = [id2room[_id][0] for _id in rg.split(LIST_SEP)]
        roomlist = [
            {
                "Number_of_Real_Rooms": "1",
                "Real_Room": room,
            }
            for room in ridlist
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
    idmap["__ID2ROOM__"] = id2room
    idmap["__ROOM_CONSTRAINTS__"] = rconstraints


def get_activities(idmap, fetout, scenario):
    fetlist = []
    next_activity_id(reset = True)
    id2group = idmap["__ID2GROUP__"]
    id2subject = idmap["__ID2SUBJECT__"]
    id2teacher = idmap["__ID2TEACHER__"]
    id2room = idmap["__ID2ROOM__"]
    multisubjects = set()
    course2activities = {}
    idmap["__COURSE2ACTIVITIES__"] = course2activities
    subject_activities = SubjectGroupActivities(idmap["__CLASS_GROUP_ATOMS__"])
    idmap["__SUBJECT_ACTIVITIES__"] = subject_activities
    for node in scenario[_Course]:
        tlist = node[_Teachers].split(LIST_SEP)
        slist = node[_Subjects].split(LIST_SEP)
        glist = node[_Groups].split(LIST_SEP)
        _pr = node.get(_PreferredRooms)
        rlist = _pr.split(LIST_SEP) if _pr else []
        # Now convert to fet forms
        tidlist = [id2teacher[t][0] for t in tlist]
        gidlist = [id2group[g] for g in glist]
        sbj = ",".join(id2subject[s][0] for s in slist)
        if len(slist) > 1 and sbj not in multisubjects:
            # Invent a new subject
            sbjlist = fetout["Subjects_List"]["Subject"]
            sbjlist.append({"Name": sbj, "Comments": f"MULTI_{sbj}"})
            multisubjects.add(sbj)
#TODO: rooms
        ridlist = [id2room[r][0] for r in rlist]

        ## Generate the activity or activities
        # Divide lessons up according to duration
        total_duration = int(float(node[_HoursPerWeek]))
        if total_duration == 0:
#TODO
            print("HELP! Epochenfach")
            continue

#TODO: What are the possibilities for this field?
        # Take only the first value
        dlm = node[_DoubleLessonMode].split(",")[0]
        ll = int(dlm)
        lessons = []
        nl = total_duration
        while nl:
            if nl < ll:
                # reduced length for last entry
                lessons.append(nl)
                break
            else:
                lessons.append(ll)
                nl -= ll

        id0 = str(next_activity_id())
        aid_list = [id0]
        w365_course = node[_Id]
        activity = {
            "Id": id0,
            "Teacher": tidlist,
            "Subject": sbj,
            "Students": gidlist,
            "Active": "true",
            "Total_Duration": str(total_duration),
            "Activity_Group_Id": id0 if len(lessons) > 1 else "0",
            "Comments": w365_course,
        }
        aclist = []
        course2activities[w365_course] = aclist
        for i, ll in enumerate(lessons):
            if i > 0:
                activity = activity.copy()
                aid = str(next_activity_id())
                activity["Id"] = aid
                aid_list.append(aid)
            activity["Duration"] = str(ll)
            fetlist.append(activity)
            aclist.append(activity)

        subject_activities.subject_group_activity(
            sbj, gidlist, aid_list
        )


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
    idmap["__ACTIVITIES__"] = fetlist


#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


def build_fet_file(wzdb):
#TODO ...

    fetout = {
        "@version": FET_VERSION,
        "Mode": "Official",
        "Institution_Name": wzdb.config["SCHOOL"]
    }
    fetbase = {"fet": fetout}

    get_days(wzdb, fetout)
    get_periods(wzdb, fetout)
    get_teachers(wzdb, fetout)
    get_subjects(wzdb, fetout)
    get_groups(wzdb, fetout)

    return xmltodict.unparse(fetbase, pretty=True, indent="  ")



    scenario = indata["__SCENARIOS__"][school_state[_EditedScenario]]
    scenario_data = scenario.pop("__SCENARIO__")
    fetout["Comments"] = scenario_data[_Name]

    days = get_days(idmap, fetout, scenario)
    periods = get_periods(idmap, fetout, scenario)
    get_subjects(idmap, fetout, scenario)
    get_teachers(idmap, fetout, scenario)
    get_groups(idmap, fetout, scenario)
    fetout["Buildings_List"] = ""
    get_rooms(idmap, fetout, scenario)
    get_activities(idmap, fetout, scenario)

    ### Time constraints
    tcmap = {
        "ConstraintBasicCompulsoryTime": {
            "Weight_Percentage": "100",
            "Active": "true",
            "Comments": None,
        },
        "ConstraintMinDaysBetweenActivities": [],
    }
    day_list = [d["Name"] for d in days]        # day-tag list
    hour_list = [p["Name"] for p in periods]    # period-tag list
    ttconstraints = get_time_constraints(tcmap, idmap, day_list, hour_list)
    fetout["Time_Constraints_List"] = tcmap

#TODO: ### Space constraints
    scmap = {
        "ConstraintBasicCompulsorySpace": {
            "Weight_Percentage": "100",
            "Active": "true",
            "Comments": None,
        }
    }
    fetout["Space_Constraints_List"] = scmap

#TODO: Need to specify which "Schedule" to use
    schedules = [
        (node[_ListPosition], node[_Name], node[_Lessons])
        for node in scenario[_Schedule]
    ]
    for _, n, _ in schedules:
        print(" +++", n)

# The "Vorlage" might have only fixed lessons.
# If adding or deleting lessons, the Lessons field of the Schedule
# must be updated.

# Assume the last schedule?
    lesson_set = set(schedules[-1][-1].split(LIST_SEP))

    print("\n ****** LESSONS:")
    id2group = idmap["__ID2GROUP__"]
    clist = []
    elist = []
    course_times = {}
    epoch_times = {}
    # NOTE that I am only picking up fixed Epochenstunden ...
#TODO: Non-fixed ones cannot at present be forced to be double lessons,
# so their use is a bit limited.
    for node in scenario[_Lesson]:
        if node[_Id] not in lesson_set:
            continue
        if node[_Fixed] == "true":
            c = node.get(_Course)
            slot = (node[_Day], node[_Hour])
            if c:
                try:
                    course_times[c].append(slot)
                except KeyError:
                    course_times[c] = [slot]
            else:
                ep = node[_EpochPlan]
                try:
                    epoch_times[ep].add(slot)
                except KeyError:
                    epoch_times[ep] = {slot}

#TODO: Might want to record the ids of non-fixed lessons as these entries
# might get changed?

# Do I need the EpochPlan to discover which teachers are involved in an
# Epoch, or can I get it from the Course entries somehow? No, this is really
# not ideal. There is a tenuous connection between Epochenschienen and courses
# only when an Epochenplan has been generated: there are then lessons
# which point to the course. Maybe for now I should collect the block
# times associated with the classes (I suppose using the EpochPlan to
# identify the classes is best? – it also supplies the name tag), then
# go through the block courses to find those in a block (test EpochWeeks?)
# and hence any other infos ... especially the teachers, I suppose.

    starttimes = {}
    aclist = fetout["Activities_List"]["Activity"]
    sids = idmap["__SUBJECT_SET__"]
    subjects = fetout["Subjects_List"]["Subject"]
    for ep, times in epoch_times.items():
        node = idmap[ep]
        lesson_times = process_lesson_times(times)
        #print(" -e-", node[_Shortcut], lesson_times)
        cl_list = [id2group[id] for id in node[_Groups].split(LIST_SEP)]
        #print("   :::", ", ".join(cl_list))
        sid = node[_Shortcut]
        if sid not in sids:
            subjects.append({"Name": sid, "Comments": node[_Name]})
            sids.add(sid)
        td = 0
        dhn = []
        for n, dh in lesson_times.items():
            for d, h in dh:
                dhn.append((d, h, n))
                td += n
        id0 = str(next_activity_id())
        aid = id0
        activity = {
            "Id": aid,
            #"Teacher": None,
            "Subject": sid,
            "Students": cl_list,
            "Active": "true",
            "Total_Duration": str(td),
            "Activity_Group_Id": id0 if len(dhn) > 1 else "0",
            "Comments": f"BLOCK:{node[_Name]}",
        }
        cpy = False
        for d, h, n in dhn:
            if cpy:
                activity = activity.copy()
                aid = str(next_activity_id())
                activity["Id"] = aid
            else:
                cpy = True
            activity["Duration"] = str(n)
            aclist.append(activity)
            starttimes[aid]= {
                "Weight_Percentage": "100",
                "Activity_Id": aid,
                "Preferred_Day": day_list[d],
                "Preferred_Hour": hour_list[h],
                "Permanently_Locked": "true",
                "Active": "true",
                "Comments": None,
            }

#TODO: Might want to represent the Epochs as single course items in fet?
# That would be necessary if the teachers are included (but consider also
# the possibility of being involved in other Epochen (e.g. Mittelstufe),
# which might be different ... That's difficult to handle anyway.
# Perhaps it's easier to put no teachers in and block the teachers
# concerned in "Absences"?

# The c-tags below identify fixed lessons. <c> is the w365-Course-id. So I
# would need a mapping Course-id to the activities associated with it.

    course2activities = idmap["__COURSE2ACTIVITIES__"]
    for c, times in course_times.items():
        lesson_times = process_lesson_times(times)
        #print(" -c-", c, lesson_times)
        try:
            cacts = course2activities[c]
        except KeyError:
            print("****** course2activities[c] ******:", c)
            continue
        for activity in course2activities[c]:
            n = int(activity["Duration"])
            dhl = lesson_times.get(n)
            if dhl:
                d, h = dhl.pop()
                aid = activity["Id"]
                starttimes[aid] = {
                    "Weight_Percentage": "100",
                    "Activity_Id": aid,
                    "Preferred_Day": day_list[d],
                    "Preferred_Hour": hour_list[h],
                    "Permanently_Locked": "true",
                    "Active": "true",
                    "Comments": None,
                }
# That assumes the input data has matching items
    tcmap["ConstraintActivityPreferredStartingTime"] = list(starttimes.values())

#TODO
    idmap["__STARTTIMES__"] = starttimes

    idmap["__SUBJECT_ACTIVITIES__"].constraint_day_separation(
        starttimes,
        tcmap["ConstraintMinDaysBetweenActivities"]
    )

    return xmltodict.unparse(fetbase, pretty=True, indent="  ")


#-----------------------------------------------------------------------


if __name__ == "__main__":
    from core.base import DATAPATH
    from w365.wz_w365.w365base import W365_DB, read_active_scenario
    from w365.wz_w365.rooms import read_rooms
    from w365.wz_w365.subjects import read_subjects
    from w365.wz_w365.teachers import read_teachers
    from w365.wz_w365.class_groups import read_groups
    from w365.wz_w365.activities import read_activities
    from w365.wz_w365.timeslots import read_days, read_periods

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

    read_days(w365)
    read_periods(w365)
    read_groups(w365)
    read_subjects(w365)
    read_teachers(w365)
    read_rooms(w365)
    read_activities(w365)
    # Add config items to database
    w365.config2db()

#TODO
    fetxml = build_fet_file(w365)
    print("§XML:", fetxml)
    quit(1)

    outfile = f'{os.path.basename(w365path).rsplit(".", 1)[0]}.fet'
    outpath = os.path.join(os.path.dirname(w365path), outfile)
    with open(outpath, "w", encoding = "utf-8") as fh:
        fh.write(fetxml)
    print("\n  ==>", outpath)
