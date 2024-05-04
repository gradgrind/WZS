from itertools import product

import xmltodict

from w365base import (
    read_w365,
    LIST_SEP,
    absences,
    categories,

    ## Item types
    _Course,
    _Day,
    _Group,
    _Lesson,
    _Period,     # lesson slot
    _Room,
    _Schedule,
    _Subject,
    _Teacher,
    _Year,
    _YearDiv,

    ## Fields:
    _Absences,
    _capacity,
    _Categories,
    _ContainerId,
    _Day,
    _day,
    _DoubleLessonMode,
    _EditedScenario,
    _EpochPlan,
    _EpochPlanYear,
    _Firstname,
    _Fixed,
    _ForceFirstHour,
    _Groups,
    _Hour,
    _hour,
    _HoursPerWeek,
    _Id,
    _Lessons,
    _Letter,
    _Level,
    _ListPosition,
    _MaxDays,
    _MaxLessonsPerDay,
    _MaxGapsPerDay,
    _MiddayBreak,
    _MinLessonsPerDay,
    _Name,
    _NumberOfAfterNoonDays,
    _PreferredRooms,
    _RoomGroup,
    _Rooms,
    _SchoolName,
    _Shortcut,
    _Subjects,
    _Teachers,
    _YearDivs,
)
from fet_support import next_activity_id, AG_SEP
from constraints import get_time_constraints, EXTRA_SUBJECTS
from constraints_subject_separation import (
    SubjectGroupActivities,
)

###-----


class AG(frozenset):
    def __repr__(self):
        return f"{{*{', '.join(sorted(self))}*}}"

    def __str__(self):
        return AG_SEP.join(sorted(self))


def make_class_groups(class_group_atoms, classtag, divs):
    if not divs:
        class_group_atoms[classtag] = {"": set()}
        return {
            "Name": classtag,
            "Number_of_Students": "0",
            #"Comments": "",
            # The information regarding categories, divisions of each category,
            # and separator is only used in the divide year automatically by
            # categories dialog in fet.
            "Number_of_Categories": "0",
            "Separator": AG_SEP,
        }
    cgmap = {
        "Name": classtag,
        "Number_of_Students": "0",
        #"Comments": "",
        # The information regarding categories, divisions of each category,
        # and separator is only used in the divide year automatically by
        # categories dialog in fet.
        "Number_of_Categories": "1",
        "Separator": AG_SEP,
    }
    # Check the input
    gset = set()
    divs1 = []
    divs1x = []
    for d in divs:
        gs = []
        xg = {}
        divs1.append(gs)
        divs1x.append(xg)
        for g in d:
            assert g not in gset
            gset.add(g)
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
    # Add "categories" (atomic groups – not to be confused with the
    # "Categories" in Waldorf365 data)
    cgmap["Category"] = {
        "Number_of_Divisions": f"{len(aglist)}",
        "Division": [str(ag) for ag in aglist],
    }
    # Add groups and subgroups
    groups = []
    cgmap["Group"] = groups
    # If there is only one division, the fet-groups can be the same as
    # fet-subgroups. If there are "compound" groups, these will contain
    # "normal" groups, which then do not need additional fet-group
    # entries.
    if len(divs1) == 1:
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
    g2ag[""] = set(aglist)
    class_group_atoms[classtag] = g2ag
    #print("$g2ag:", g2ag)
    return cgmap


#=======================================================================


def get_days(idmap, fetout, scenario):
    fetlist = []
    for d in scenario[_Day]:
        fetlist.append({"Name": d[_Shortcut]})
    fetout["Days_List"] = {
        "Number_of_Days":   f"{len(fetlist)}",
        "Day": fetlist,
    }
    return fetlist


def get_periods(idmap, fetout, scenario):
    fetlist = []
    lunchbreak = []
    for i, p in enumerate(scenario[_Period]):
        # It seems to be acceptable to have no "Shortcut".
        # In that case, use the counter.
        ptag = p.get(_Shortcut) or str(i + 1)
        fetlist.append({"Name": ptag})
        if p[_MiddayBreak] == "true":
            lunchbreak.append(i)
    fetout["Hours_List"] = {
        "Number_of_Hours":   f"{len(fetlist)}",
        "Hour": fetlist,
    }
    idmap["__LUNCHPERIODS__"] = lunchbreak
    return fetlist


def get_teachers(idmap, fetout, scenario):
    fetlist = []
    tconstraints = {}
    id2teacher = {}
    for node in scenario[_Teacher]:
        tid = node[_Shortcut]
        id2teacher[node[_Id]] = (tid, node[_Name])
        fetlist.append({
            "Name": tid,
            "Target_Number_of_Hours": "0",
            "Qualified_Subjects": None,
            "Comments": f'{node[_Firstname]} {node[_Name]}'
        })
        constraints = {
            f: node[f]
            for f in (
                _MaxDays,
                _MaxLessonsPerDay,
                _MaxGapsPerDay,    # gaps
                _MinLessonsPerDay,
                _NumberOfAfterNoonDays,
            )
        }
        tconstraints[tid] = constraints
        constraints[_Absences] = absences(idmap, node)
        constraints[_Categories] = categories(idmap, node)
    fetout["Teachers_List"] = {"Teacher": fetlist}
    idmap["__ID2TEACHER__"] = id2teacher
    idmap["__TEACHER_CONSTRAINTS__"] = tconstraints
    #print("\n__TEACHER_CONSTRAINTS__", tconstraints)


def get_subjects(idmap, fetout, scenario):
    fetlist = EXTRA_SUBJECTS()
    id2subject = {}
    constraints = {}
    sids = set()
    for node in scenario[_Subject]:
        sid = node[_Shortcut]
        name = node[_Name]
        id2subject[node[_Id]] = (sid, name)
        fetlist.append({"Name": sid, "Comments": name})
        sids.add(sid)
        c = categories(idmap, node)
        if c:
            constraints[sid] = c
    fetout["Subjects_List"] = {"Subject": fetlist}
    idmap["__ID2SUBJECT__"] = id2subject
    idmap["__SUBJECT_CONSTRAINTS__"] = constraints
    idmap["__SUBJECT_SET__"] = sids


def get_groups(idmap, fetout, scenario):
    id2gtag = {node[_Id]: node[_Shortcut] for node in scenario[_Group]}
    id2div = {}
    for d in scenario[_YearDiv]:    # Waldorf365: "GradePartiton" (sic)
        name = d[_Name]
        gidlist = d[_Groups].split(LIST_SEP)
        iglist = [(id2gtag[gid], gid) for gid in gidlist]
        iglist.sort()
        id2div[d[_Id]] = iglist
        #print(f" -- {name} = {iglist}")
    ylist = []  # Collect class data for fet
#    id2year = {}
    id2group = {}
    cconstraints = {}
    class_group_atoms = {}
    for node in scenario[_Year]:   # Waldorf365: "Grade"
        cltag = f'{node[_Level]}{node.get(_Letter) or ""}'
        yid = node[_Id]
#        id2year[yid] = cltag
        id2group[yid] = cltag
        dlist = []
        divs = node.get(_YearDivs)
        if divs:
            for div in divs.split(LIST_SEP):
                glist = []
                for g, gid in id2div[div]:
                    glist.append(g)
                    id2group[gid] = f"{cltag}{AG_SEP}{g}"
                dlist.append(glist)
        #print(f'+++ {cltag}: {dlist}')
        ylist.append(make_class_groups(class_group_atoms, cltag, dlist))
        constraints = {
            f: node[f]
            for f in (
                _ForceFirstHour,
                _MaxLessonsPerDay,
                _MinLessonsPerDay,
                _NumberOfAfterNoonDays,
            )
        }
        cconstraints[cltag] = constraints
        constraints[_Absences] = absences(idmap, node)
        constraints[_Categories] = categories(idmap, node)
    fetout["Students_List"] = {"Year": ylist}
    idmap["__ID2GROUP__"] = id2group
    idmap["__YEAR_CONSTRAINTS__"] = cconstraints
    idmap["__CLASS_GROUP_ATOMS__"] = class_group_atoms
    #print('§idmap["__CLASS_GROUP_ATOMS__"]:', class_group_atoms)


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


def process_lesson_times(time_list):
    slots = {}
    day = None
    hour = None
    n = None
    for d, h in sorted(time_list):
        if d == day:
            ih = int(h)
            if ih == int(hour) + n:
                n += 1
            else:
                # A second slot on the same day ...
                t = (int(day), ih)
                try:
                    slots[n].append(t)
                except KeyError:
                    slots[n] = [t]
                hour = h
                n = 1
        else:
            if day is not None:
                t = (int(day), int(hour))
                try:
                    slots[n].append(t)
                except KeyError:
                    slots[n] = [t]
            day = d
            hour = h
            n = 1
    if day is not None:
        t = (int(day), int(hour))
        try:
            slots[n].append(t)
        except KeyError:
            slots[n] = [t]
    return slots


def build_fet(inpath):
    indata = read_w365(inpath)
    school_state = indata["__SCHOOLSTATE__"]
    idmap = indata["__IDMAP__"]
    fetout = {
        "@version": "6.18.0",
        "Mode": "Official",
        "Institution_Name": school_state[_SchoolName]
    }
    fetbase = {"fet": fetout}
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
    fpath = "w365_fms1ax"
    fpath = "w365_demo1"
    fetxml = build_fet(fpath)
    outpath = f'{fpath}.fet'
    with open(outpath, "w", encoding = "utf-8") as fh:
        fh.write(fetxml)
    print("\n  ==>", outpath)
    quit(1)

    data = read_w365(fpath)
    print("### SchoolState:")
    school_state = data["__SCHOOLSTATE__"]
    idmap = data["__IDMAP__"]
    print(school_state)
    for scen in data["__SCENARIOS__"].values():
        print(scen["__SCENARIO__"][_Name])

    scenario = data["__SCENARIOS__"][school_state[_EditedScenario]]
    scenario_data = scenario.pop("__SCENARIO__")
    outlines = []
    for sect, itemlist in scenario.items():
        outlines.append(f"\n### {sect} ({len(itemlist)})")
        for item in itemlist:
            outlines.append("::")
            for k, v in item.items():
                outlines.append(f"  {k:20} = {v}")
            amap = absences(idmap, item)
            if amap:
                outlines.append(f"** Absences: {amap}")
    with open(f'{fpath}_dict_{scenario_data[_Name]}', "w", encoding = "utf-8") as fh:
        fh.write("\n".join(outlines))
