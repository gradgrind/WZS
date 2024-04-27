"""
w365/fet/constraints.py - last updated 2024-04-23

Add constraints to the fet file.


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

#TODO: Should be got from somewhere else:
from timetable.w365.class_groups import AG_SEP
#TODO: These dependencies don't belong here! However, if I use their
# strings for potential other inputs, it might be okay?
#from timetable.w365.w365base import (
#    _Categories,
#)

from core.basic_data import pr_course
from timetable.fet.fet_support import (
    SUBJECT_LUNCH_BREAK,
    SUBJECT_FREE_AFTERNOON,
    next_activity_id,
)
from timetable.fet.lesson_constraints import lesson_constraints

#TODO: There could be a clash between the current implementation of
# lunch breaks and the max-gaps settings.

#TODO: Note that in fet it might be better to not implement stuff like
# "max. afternoons" directly, but rather to do multiple runs with
# different fixed afternoons. This might also make dealing with lunch
# breaks easier.

def EXTRA_SUBJECTS():
    return [
        {"Name": SUBJECT_LUNCH_BREAK, "Comments": "Mittagspause"},
        {"Name": SUBJECT_FREE_AFTERNOON, "Comments": "Freier Nachmittag"}
    ]


def get_time_constraints(db, fetout, daylist, periodlist):
    # Note that <constraint_list> is actually a mapping!
    not_on_same_day_list = []
    constraint_list = {
        "ConstraintBasicCompulsoryTime": {
            "Weight_Percentage": "100",
            "Active": "true",
            "Comments": None,
        },
        "ConstraintMinDaysBetweenActivities": not_on_same_day_list,
    }
    fetout["Time_Constraints_List"] = constraint_list
    afternoon_start = db.config["AFTERNOON_START_PERIOD"]
    if afternoon_start >= 0:
        afternoon_hours = set(periodlist[afternoon_start:])
    else:
        afternoon_hours = set()
    lunchbreak = db.config["LUNCHBREAK"] # list of period indexes (ints, not tags)
    lunchbreak_hours = {periodlist[h] for h in lunchbreak}
    #print("§lb", lunchbreak_hours)
    #print("§pm", afternoon_hours)
    n_days = len(daylist)
    n_hours = len(periodlist)
#TODO: New (old) approach to lunch-breaks, with dummy lessons:
    # Each atomic group gets a lunch break on days where the class is
    # available in the whole range.
#!!! It needs the absences, which are done further below !!!

#TODO: This only accepts contiguous lunch-break slots:
    if lunchbreak:
        lblist = sorted(lunchbreak, reverse = True)
        p0 = lblist.pop()
#TODO
        assert lblist, "Single lunch slot not currently supported"
        # In that case a "not available" would perhaps be more appropriate
        # (or simply leaving no slot there ...)
        p = p0
        while lblist:
            p1 = lblist.pop()
            assert p1 == p + 1, "Lunch slots must be contiguous"
            p = p1

#TODO-- not approppriate in every case
        # Lunch breaks for all teachers
        constraint_list["ConstraintTeachersMaxHoursDailyInInterval"] = {
            "Weight_Percentage": "100",
            "Interval_Start_Hour": periodlist[p0],
            "Interval_End_Hour": periodlist[p + 1],
            "Maximum_Hours_Daily": str(p - p0),
            "Active": "true",
            "Comments": None,
        }

# This constraint can come into conflict with gap limiting. That is
# probably less of a problem for teachers than for classes. It could
# well be that classes should have no gaps at all, so the constraint
# "ConstraintStudentsMaxHoursDailyInInterval" is not used. Dummy
# lunch-break lessons are used instead. However, it may be that some
# more consideration of this point is necessary: for example, why is
# a free lesson not acceptable while a lunch-break (essentially a free
# lesson!) is compulsory?

    ### Teacher constraints
    t_absence_list = []     # teachers, not-available times
    t_max_days_list = []    # teachers, max days per week
    t_maxlessonsperday_list = []  # teachers, max lesson periods per day
    t_maxgapsperday_list = []  # teachers, max gaps per day
    t_minlessonsperday_list = []  # teachers, min lesson periods per day
    t_afternoon_list = []   # teachers, max teaching afternoons

#    return
#?
    for node in db.tables["TEACHERS"]:
        x = node.get("EXTRA")
        if x:
            print("EXTRA:", x)
#        if tid not in used:
#            continue
# ...
        tid = node["ID"]
        cdata = node["CONSTRAINTS"]
        afternoons = cdata["NumberOfAfterNoonDays"]
        n_afternoons = int(afternoons)
        nt_days = n_days
        try:
            cdata_absences = node["NOT_AVAILABLE"]
        except KeyError:
            pass
        else:
            for d, hl in cdata_absences.items():
                if len(hl) >= n_hours:
#TODO
                    assert len(hl) == n_hours
                    nt_days -= 1
#TODO count blocked afternoons



        maxdays = cdata["MaxDays"]
        n_maxdays = int(maxdays)
        if n_maxdays < n_days:
            t_max_days_list.append({
                "Weight_Percentage": "100",
                "Teacher_Name": tid,
                "Max_Days_Per_Week": maxdays,
                "Active": "true",
                "Comments": "",
            })
        else:
            n_maxdays = n_days


        # If "0" afternoons is set this should be set as absence, not as
        # an additional constraint here.
        absences = {}

#TODO: This could lead to some tricky constraint interactions!
# If there are fixed absences, the constraints could depend on exactly
# which days are chosen – which could be a big problem ...
# Perhaps I should choose the days with the most free slots?
# Actually, teachers can (mostly) be a bit more flexible than classes, so
# perhaps the initial approach could work for them.
        if n_afternoons < n_maxdays:
            assert afternoon_start >= 0
            if n_afternoons == 0:
                for d in range(len(daylist)):
                    absences[d] = afternoon_hours.copy()
            else:
                t_afternoon_list.append({
                    "Weight_Percentage": "100",
                    "Teacher_Name": tid,
                    "Interval_Start_Hour": periodlist[afternoon_start],
                    "Interval_End_Hour": None,  # end of day
                    "Max_Days_Per_Week": afternoons,
                    "Active": "true",
                    "Comments": "",
                })

# cdata_absences is possibly undefined (see above)
        if cdata_absences:
            for d, plist in cdata_absences.items():
                try:
                    pset = absences[d]
                except KeyError:
                    pset = {periodlist[h] for h in plist}
                    absences[d] = pset
                else:
                    pset.update(periodlist[h] for h in plist)
        if absences:
            natlist = []
            for d in sorted(absences):
                day = daylist[d]
                pset = absences[d]
                for h in periodlist:
                    if h in pset:
                        natlist.append({
                            "Day": day,     # e.g. "Do."
                            "Hour": h       # e.g. "B"
                        })
            t_absence_list.append({
                "Weight_Percentage": "100",
                "Teacher": tid,
                "Number_of_Not_Available_Times": str(len(natlist)),
                "Not_Available_Time": natlist,
                "Active": "true",
                "Comments": "",
            })

        maxlessonsperday = cdata["MaxLessonsPerDay"]
        if int(maxlessonsperday) < n_hours:
            t_maxlessonsperday_list.append({
                # Can be < 100, but not really recommended:
                "Weight_Percentage": "100",
                "Teacher_Name": tid,
                "Maximum_Hours_Daily": maxlessonsperday,
                "Active": "true",
                "Comments": "",
            })

        maxgapsperday = cdata["MaxGapsPerDay"]
        if int(maxgapsperday) < n_hours:
            t_maxgapsperday_list.append({
                "Weight_Percentage": "100",
                "Teacher_Name": tid,
                "Max_Gaps": maxgapsperday,
                "Active": "true",
                "Comments": "",
            })

        minlessonsperday = cdata["MinLessonsPerDay"]
        if int(minlessonsperday) > 1:
            t_minlessonsperday_list.append({
                "Weight_Percentage": "100",
                "Teacher_Name": tid,
                "Minimum_Hours_Daily": minlessonsperday,
                "Allow_Empty_Days": "true",
                "Active": "true",
                "Comments": "",
            })

#TODO
#        categories = cdata[_Categories]

    constraint_list["ConstraintTeacherIntervalMaxDaysPerWeek"] = t_afternoon_list
    constraint_list["ConstraintTeacherNotAvailableTimes"] = t_absence_list
    constraint_list["ConstraintTeacherMaxDaysPerWeek"] = t_max_days_list
    constraint_list["ConstraintTeacherMaxHoursDaily"] = t_maxlessonsperday_list
    constraint_list["ConstraintTeacherMaxGapsPerDay"] = t_maxgapsperday_list
    constraint_list["ConstraintTeacherMinHoursDaily"] = t_minlessonsperday_list

    ### Class constraints
    cl_afternoon_list = []
    cl_absence_list = []
    cl_hour0_list = []
    cl_maxlessonsperday_list = []  # classes, max lesson periods per day
    #cl_maxgapsperday_list = []  # classes, max gaps per day
    cl_minlessonsperday_list = []  # classes, min lesson periods per day
    week_gaps_list = []

    atomic_groups = db.full_atomic_groups
    for node in db.tables["CLASSES"]:
        clid = node["ID"]
        cdata = node["CONSTRAINTS"]
#TODO!!!!! Could there be a filter for classes with too few subjects?
        week_gaps_list.append({
            "Weight_Percentage": "100",
            "Max_Gaps": "0",
            "Students": clid,
            "Active": "true",
            "Comments": "",
        })
        afternoons = cdata["NumberOfAfterNoonDays"]
        n_afternoons = int(afternoons)
        # If "0" afternoons is set this should be set as absence, not as
        # an additional constraint here.
        absences = {}
        if n_afternoons < n_days:
            if n_afternoons == 0:
                for d in range(len(daylist)):
                    absences[d] = afternoon_hours.copy()
#            else:
#TODO: Do I want to rather, in combination with lunchbreaks, add special
# dummy last-of-day lessons (filling the afternoon slots)?
#                cl_afternoon_list.append({
#                    "Weight_Percentage": "100",
#                    "Students": clid,
#                    "Interval_Start_Hour": periodlist[AFTERNOON_LESSONS[0]],
#                    "Interval_End_Hour": None,  # end of day
#                    "Max_Days_Per_Week": afternoons,
#                    "Active": "true",
#                    "Comments": "",
#                })

        cdata_absences = node.get("NOT_AVAILABLE")
        if cdata_absences:
            for d, plist in cdata_absences.items():
                try:
                    pset = absences[d]
                except KeyError:
                    pset = {periodlist[h] for h in plist}
                    absences[d] = pset
                else:
                    pset.update(periodlist[h] for h in plist)
        lbdays = set(daylist)
        aftdays = set(daylist)
        if absences:
            natlist = []
            for d in sorted(absences):
                day = daylist[d]
                pset = absences[d]
                if lunchbreak_hours & pset:
                    lbdays.remove(day)
                if afternoon_hours <= pset:
                    aftdays.remove(day)
                for h in periodlist:
                    if h in pset:
                        natlist.append({
                            "Day": day,     # e.g. "Do."
                            "Hour": h       # e.g. "B"
                        })
            cl_absence_list.append({
                "Weight_Percentage": "100",
                "Students": clid,
                "Number_of_Not_Available_Times": str(len(natlist)),
                "Not_Available_Time": natlist,
                "Active": "true",
                "Comments": "",
            })
        #print("§§§§aft:", clid, aftdays)
        #print("§§§§lb:", lbdays)
        #print("§absences:", absences)

        ## Do lunch-breaks, afternoons and basic days-between activities
        kags = sorted(atomic_groups[clid])
        #print("\n§kags:", clid, kags)
        activities = fetout["Activities_List"]["Activity"]
        if n_afternoons:
            n_ad = len(aftdays)
            # I am assuming that a free afternoon requires no lunch break
            if n_afternoons < n_ad:
                n_lb = n_afternoons
                n_blocker = n_ad - n_afternoons
            else:
                n_lb = n_ad
                n_blocker = 0
            aftlen = str(len(afternoon_hours))
            # Generate blockers for all atomic groups
            for kag in kags:
                aids = []
                # afternoon blockers
                for i in range(n_blocker):
                    # Add activity
                    aid = str(next_activity_id())
                    activities.append({
                        "Id": aid,
                        #"Teacher": None,
                        "Subject": SUBJECT_FREE_AFTERNOON,
                        "Students": kag,
                        "Active": "true",
                        "Total_Duration": aftlen,
                        "Duration": aftlen,
                        "Activity_Group_Id": "0",
                        "Comments": "",
                    })
                    aids.append(aid)
#TODO: Might also need to constrain starting time
                # lunch breaks
                for i in range(n_lb):
                    # Add activity
                    aid = str(next_activity_id())
                    activities.append({
                        "Id": aid,
                        #"Teacher": None,
                        "Subject": SUBJECT_LUNCH_BREAK,
                        "Students": kag,
                        "Active": "true",
                        "Total_Duration": "1",
                        "Duration": "1",
                        "Activity_Group_Id": "0",
                        "Comments": "",
                    })
                    aids.append(aid)
                # Constrain to different days
                if len(aids) > 1:
                    not_on_same_day_list.append({
                        "Weight_Percentage": "100",
                        "Consecutive_If_Same_Day": "true",
                        "Number_of_Activities": str(len(aids)),
                        "Activity_Id": aids,
                        "MinDays": "1",
                    })

        if cdata["ForceFirstHour"] == "false":
            cl_hour0_list.append({
                "Weight_Percentage": "100",
                "Max_Beginnings_At_Second_Hour": str(len(daylist)),
                "Students": clid,
                "Active": "true",
                "Comments": "",
            })

        maxlessonsperday = cdata["MaxLessonsPerDay"]
        if int(maxlessonsperday) < n_hours:
            cl_maxlessonsperday_list.append({
                # Can be < 100, but not really recommended:
                "Weight_Percentage": "100",
                "Students": clid,
                "Maximum_Hours_Daily": maxlessonsperday,
                "Active": "true",
                "Comments": "",
            })

        minlessonsperday = cdata["MinLessonsPerDay"]
        if int(minlessonsperday) > 1:
            cl_minlessonsperday_list.append({
                "Weight_Percentage": "100",
                "Students": clid,
                "Minimum_Hours_Daily": minlessonsperday,
                "Allow_Empty_Days": "false",
                "Active": "true",
                "Comments": "",
            })

#TODO
        categories = node.get("EXTRA")
        if categories:
            print("EXTRA:", categories)

    lesson_constraints(db, fetout, daylist, periodlist)
    constraint_list["ConstraintStudentsSetIntervalMaxDaysPerWeek"] = cl_afternoon_list
    constraint_list["ConstraintStudentsSetNotAvailableTimes"] = cl_absence_list
    constraint_list["ConstraintStudentsSetEarlyMaxBeginningsAtSecondHour"] = cl_hour0_list
    constraint_list["ConstraintStudentsSetMaxHoursDaily"] = cl_maxlessonsperday_list
    constraint_list["ConstraintStudentsSetMinHoursDaily"] = cl_minlessonsperday_list
    lblist = [
        {"Preferred_Starting_Day": d, "Preferred_Starting_Hour": h}
        for d in daylist
        for h in lunchbreak_hours
    ]
    #print("§LUNCHBREAKS:", lblist)
    constraint_list["ConstraintActivitiesPreferredStartingTimes"] = {
        "Weight_Percentage": "100",
        "Teacher_Name": None,
        "Students_Name": None,
        "Subject_Name": SUBJECT_LUNCH_BREAK,
        "Activity_Tag_Name": None,
        "Duration": None,
        "Number_of_Preferred_Starting_Times": str(len(lblist)),
        "Preferred_Starting_Time": lblist,
        "Active": "true",
        "Comments": "",
    }
    constraint_list["ConstraintActivitiesEndStudentsDay"] = [
        {
            "Weight_Percentage": "100",
            "Teacher_Name": None,
            "Students_Name": None,
            "Subject_Name": SUBJECT_FREE_AFTERNOON,
            "Activity_Tag_Name": None,
            "Active": "true",
            "Comments": "",
        },
        # This is an attempt to get the lunch-break as late as possible.
        # This can help prevent lunch-breaks being allocated before the
        # last lesson on days where no afternoons would be necessary.
        # But it is not ideal, especially when the lunch-breaks should be
        # more evenly distributed!
        {
            "Weight_Percentage": "70",
            "Teacher_Name": None,
            "Students_Name": None,
            "Subject_Name": SUBJECT_LUNCH_BREAK,
            "Activity_Tag_Name": None,
            "Active": "true",
            "Comments": "",
        },
    ]
    constraint_list["ConstraintStudentsSetMaxGapsPerWeek"] = week_gaps_list
#<ConstraintStudentsMaxGapsPerWeek>
#   <Weight_Percentage>100</Weight_Percentage>
#   <Max_Gaps>0</Max_Gaps>
#   <Active>true</Active>
#   <Comments></Comments>
#</ConstraintStudentsMaxGapsPerWeek>


def get_space_constraints(db, fetout):
    # Note that <constraint_list> is actually a mapping!
    not_on_same_day_list = []
    constraint_list = {
        "ConstraintBasicCompulsorySpace": {
            "Weight_Percentage": "100",
            "Active": "true",
            "Comments": None,
        }
    }
    fetout["Space_Constraints_List"] = constraint_list
    key2node = db.key2node
    vrnum = 0    # index for additional virtual rooms
    c_room = []
    c_rooms = []
    for node in db.tables["COURSES"]:
        try:
            activities = node["$ACTIVITIES"]
            #print("§course+++:", pr_course(db, node))
        except KeyError:
            #print("§course:", pr_course(db, node))
            continue
        room_items = node["$ROOM_SET"]
        if len(room_items) > 1:
            # Make a new virtual room and add it as a single room
            rsets = []
            for itemr in sorted(room_items):
                n = 0
                ridlist = []
                for r in itemr:
                    if r in db.virtual_rooms:
                        REPORT_ERROR(
                            f"Kurs {pr_course(db, node)}: Eine Raumgruppe"
                            f" ({r}) darf für einen Kurs mit mehreren"
                            " Räumen nicht eingesetzt werden."
                        )
                    else:
                        ridlist.append(r)
                        n += 1
                if n == 0:
                    continue
                rsets.append({
                    "Number_of_Real_Rooms": str(n),
                    "Real_Room": ridlist,
                })
            if len(rsets) > 1:
                # This needs to be added to the rooms list, but not
                # remembered in any other way. The data for later
                # extraction will be the "Real_Room" entries.
                vrnum += 1
                vr = f"_VR_{vrnum:03}"
                fetout["Rooms_List"]["Room"].append({
                    "Name": vr,
                    "Building": None,
                    "Capacity": "30000",
                    "Virtual": "true",
                    "Number_of_Sets_of_Real_Rooms": str(len(rsets)),
                    "Set_of_Real_Rooms": rsets,
                    "Comments": None,
                })
                rl = [vr]
            elif rsets:
                rl = rsets[0]["Real_Room"]
            else:
                continue
        else:
            try:
                rl = sorted(room_items.pop())
            except KeyError:
                continue
        n = len(rl)
        if n > 1:
#TODO Shall I allow virtual rooms in here? It would need testing ...
            # ConstraintActivityPreferredRooms
            for a in activities:
                c_rooms.append({
                    "Weight_Percentage": "100",
                    "Activity_Id": a["Id"],
                    "Number_of_Preferred_Rooms": str(n),
                    "Preferred_Room": rl,
                    "Active": "true",
                    "Comments": None,
                })
        else:
            for a in activities:
                c_room.append({
                    "Weight_Percentage": "100",
                    "Activity_Id": a["Id"],
                    "Room": rl[0],
                    "Permanently_Locked": "true",
                    "Active": "true",
                    "Comments": None,
                })
    constraint_list["ConstraintActivityPreferredRoom"] = c_room
    constraint_list["ConstraintActivityPreferredRooms"] = c_rooms


'''
<ConstraintActivityPreferredRoom>
    <Weight_Percentage>100</Weight_Percentage>
    <Activity_Id>596</Activity_Id>
    <Room>Sp</Room>
    <Permanently_Locked>true</Permanently_Locked>
    <Active>true</Active>
    <Comments></Comments>
</ConstraintActivityPreferredRoom>
<ConstraintActivityPreferredRooms>
    <Weight_Percentage>100</Weight_Percentage>
    <Activity_Id>212</Activity_Id>
    <Number_of_Preferred_Rooms>2</Number_of_Preferred_Rooms>
    <Preferred_Room>EuU</Preferred_Room>
    <Preferred_Room>EuO</Preferred_Room>
    <Active>true</Active>
    <Comments></Comments>
</ConstraintActivityPreferredRooms>
# Presumably, PreferredRooms should not permit the inclusion of virtual
# rooms. Or would it be useful to allow a choice of virtual rooms?
# fet seems to allow that ...

# A virtual room with choices:
<Room>
    <Name>VVX</Name>
    <Building></Building>
    <Capacity>30000</Capacity>
    <Virtual>true</Virtual>
    <Number_of_Sets_of_Real_Rooms>2</Number_of_Sets_of_Real_Rooms>
    <Set_of_Real_Rooms>
        <Number_of_Real_Rooms>1</Number_of_Real_Rooms>
        <Real_Room>Orch</Real_Room>
    </Set_of_Real_Rooms>
    <Set_of_Real_Rooms>
        <Number_of_Real_Rooms>4</Number_of_Real_Rooms>
        <Real_Room>01G</Real_Room>
        <Real_Room>02G</Real_Room>
        <Real_Room>03G</Real_Room>
        <Real_Room>04G</Real_Room>
    </Set_of_Real_Rooms>
    <Comments></Comments>
</Room>

# The post-generation fet file seems to double the room constraints
# with virtual rooms and multiple rooms:
<ConstraintActivityPreferredRoom>
    <Weight_Percentage>100</Weight_Percentage>
    <Activity_Id>457</Activity_Id>
    <Room>KP12</Room>
    <Permanently_Locked>true</Permanently_Locked>
    <Active>true</Active>
    <Comments></Comments>
</ConstraintActivityPreferredRoom>
<ConstraintActivityPreferredRoom>
    <Weight_Percentage>100</Weight_Percentage>
    <Activity_Id>1</Activity_Id>
    <Room>k13</Room>
    <Permanently_Locked>true</Permanently_Locked>
    <Active>true</Active>
    <Comments></Comments>
</ConstraintActivityPreferredRoom>
<ConstraintActivityPreferredRooms>
    <Weight_Percentage>100</Weight_Percentage>
    <Activity_Id>71</Activity_Id>
    <Number_of_Preferred_Rooms>2</Number_of_Preferred_Rooms>
    <Preferred_Room>k5</Preferred_Room>
    <Preferred_Room>fsMS</Preferred_Room>
    <Active>true</Active>
    <Comments></Comments>
</ConstraintActivityPreferredRooms>
<ConstraintActivityPreferredRoom>
    <Weight_Percentage>100</Weight_Percentage>
    <Activity_Id>71</Activity_Id>
    <Room>k5</Room>
    <Permanently_Locked>false</Permanently_Locked>
    <Active>true</Active>
    <Comments></Comments>
</ConstraintActivityPreferredRoom>
<ConstraintActivityPreferredRoom>
    <Weight_Percentage>100</Weight_Percentage>
    <Activity_Id>457</Activity_Id>
    <Room>KP12</Room>
    <Number_of_Real_Rooms>3</Number_of_Real_Rooms>
    <Real_Room>ku</Real_Room>
    <Real_Room>st</Real_Room>
    <Real_Room>k12</Real_Room>
    <Permanently_Locked>false</Permanently_Locked>
    <Active>true</Active>
    <Comments></Comments>
</ConstraintActivityPreferredRoom>
'''
