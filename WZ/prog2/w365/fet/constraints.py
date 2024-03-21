from w365.wz_w365.w365base import (
    _Absences,
    _Categories,
    _MaxDays,
    _MaxGapsPerDay,    # gaps
    _MaxLessonsPerDay,
    _MinLessonsPerDay,
    _NumberOfAfterNoonDays,
    _ForceFirstHour,
)
from w365.fet.fet_support import (
    AG_SEP,
    SUBJECT_LUNCH_BREAK,
    SUBJECT_FREE_AFTERNOON,
    next_activity_id,
)

#TODO: There could be a clash between the current implementation of
# lunch breaks and the max-gaps settings.

#TODO: Need to define somehow what an afternoon is!!!
# Where does this get set?
AFTERNOON_LESSONS = [6, 7, 8]   # 0-based indexes to period list


def EXTRA_SUBJECTS():
    return [
        {"Name": SUBJECT_LUNCH_BREAK, "Comments": "Mittagspause"},
        {"Name": SUBJECT_FREE_AFTERNOON, "Comments": "Freier Nachmittag"}
    ]


def get_time_constraints(constraint_list, idmap, daylist, periodlist):
    # Note that <constraint_list> is actually a mapping!

    afternoon_hours = {periodlist[h] for h in AFTERNOON_LESSONS}
    lunchbreak = idmap["__LUNCHPERIODS__"] # list of period indexes (ints, not tags)
    lunchbreak_hours = {periodlist[h] for h in lunchbreak}
    n_days = len(daylist)
    n_hours = len(periodlist)
#TODO: New (old) approach to lunch-breaks, with dummy lessons:
    # Each atomic group gets a lunch break on days where the class is
    # available in the whole range.
#!!! It needs the absences, which are done further below !!!

    class_group_atoms = idmap["__CLASS_GROUP_ATOMS__"]

#TODO: This only accepts contiguous break slots:
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

        # Lunch breaks for all teachers
        constraint_list["ConstraintTeachersMaxHoursDailyInInterval"] = {
            "Weight_Percentage": "100",
            "Interval_Start_Hour": periodlist[p0],
            "Interval_End_Hour": periodlist[p + 1],
            "Maximum_Hours_Daily": str(p - p0),
            "Active": "true",
            "Comments": None,
        }

#TODO: This is a problem for gap limiting
#        # Lunch breaks for all students
#        constraint_list["ConstraintStudentsMaxHoursDailyInInterval"] = {
#            "Weight_Percentage": "100",
#            "Interval_Start_Hour": periodlist[p0],
#            "Interval_End_Hour": periodlist[p + 1],
#            "Maximum_Hours_Daily": str(p - p0),
#            "Active": "true",
#            "Comments": None,
#        }

    ### Teacher constraints
    t_absence_list = []     # teachers, not-available times
    t_max_days_list = []    # teachers, max days per week
    t_maxlessonsperday_list = []  # teachers, max lesson periods per day
    t_maxgapsperday_list = []  # teachers, max gaps per day
    t_minlessonsperday_list = []  # teachers, min lesson periods per day
    t_afternoon_list = []   # teachers, max teaching afternoons
    for tid, cdata in idmap["__TEACHER_CONSTRAINTS__"].items():
#        if tid not in used:
#            continue
# ...
        afternoons = cdata[_NumberOfAfterNoonDays]
        n_afternoons = int(afternoons)
        # If "0" afternoons is set this should be set as absence, not as
        # an additional constraint here.
        absences = {}

#TODO: This could lead to some tricky constraint interactions!
# If there are fixed absences, the constraints could depend on exactly
# which days are chosen – which, could be a big problem ...
# Perhaps I should choose the days with the most free slots?
# Actually, teachers can (mostly) be a bit more flexible than classes, so
# perhaps the initial approach could work for them.
        maxdays = cdata[_MaxDays]
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
        if n_afternoons < n_maxdays:
            if n_afternoons == 0:
                for day in daylist:
                    absences[day] = {periodlist[p] for p in AFTERNOON_LESSONS}
            else:
                t_afternoon_list.append({
                    "Weight_Percentage": "100",
                    "Teacher_Name": tid,
                    "Interval_Start_Hour": periodlist[AFTERNOON_LESSONS[0]],
                    "Interval_End_Hour": None,  # end of day
                    "Max_Days_Per_Week": afternoons,
                    "Active": "true",
                    "Comments": "",
                })
        cdata_absences = cdata[_Absences]
        if cdata_absences:
            for d, plist in cdata_absences.items():
                day = daylist[d]
                try:
                    pset = absences[day]
                except KeyError:
                    pset = {periodlist[h] for h in plist}
                    absences[day] = pset
                else:
                    pset.update(periodlist[h] for h in plist)
        if absences:
            natlist = []
            for d, pset in absences.items():
                for h in periodlist:
                    if h in pset:
                        natlist.append({
                            "Day": d,   # e.g. "Do."
                            "Hour": h   # e.g. "B"
                        })
            t_absence_list.append({
                "Weight_Percentage": "100",
                "Teacher": tid,
                "Number_of_Not_Available_Times": str(len(natlist)),
                "Not_Available_Time": natlist,
                "Active": "true",
                "Comments": "",
            })

        maxlessonsperday = cdata[_MaxLessonsPerDay]
        if int(maxlessonsperday) < n_hours:
            t_maxlessonsperday_list.append({
                # Can be < 100, but not really recommended:
                "Weight_Percentage": "100",
                "Teacher_Name": tid,
                "Maximum_Hours_Daily": maxlessonsperday,
                "Active": "true",
                "Comments": "",
            })

        maxgapsperday = cdata[_MaxGapsPerDay]
        if int(maxgapsperday) < n_hours:
            t_maxgapsperday_list.append({
                "Weight_Percentage": "100",
                "Teacher_Name": tid,
                "Max_Gaps": maxgapsperday,
                "Active": "true",
                "Comments": "",
            })

        minlessonsperday = cdata[_MinLessonsPerDay]
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
        categories = cdata[_Categories]


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
    for clid, cdata in idmap["__YEAR_CONSTRAINTS__"].items():
#TODO!!!!! Could there be a filter for classes with too few subjects?
        if clid in ("12", "13"):
            week_gaps_list.append({
                "Weight_Percentage": "100",
                "Max_Gaps": "0",
                "Students": clid,
                "Active": "true",
                "Comments": "",
            })
        afternoons = cdata[_NumberOfAfterNoonDays]
        n_afternoons = int(afternoons)
        # If "0" afternoons is set this should be set as absence, not as
        # an additional constraint here.
        absences = {}

        if n_afternoons == 0:
            for day in daylist:
                absences[day] = {periodlist[p] for p in AFTERNOON_LESSONS}

        if n_afternoons < n_days:
            if n_afternoons == 0:
                for day in daylist:
                    absences[day] = {periodlist[p] for p in AFTERNOON_LESSONS}
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

        cdata_absences = cdata[_Absences]
        if cdata_absences:
            for d, plist in cdata_absences.items():
                day = daylist[d]
                try:
                    pset = absences[day]
                except KeyError:
                    pset = {periodlist[h] for h in plist}
                    absences[day] = pset
                else:
                    pset.update(periodlist[h] for h in plist)
        lbdays = set(daylist)
        aftdays = set(daylist)
        if absences:
            natlist = []
            for d, pset in absences.items():
                if lunchbreak_hours & pset:
                    lbdays.remove(d)
                if afternoon_hours <= pset:
                    aftdays.remove(d)
                for h in periodlist:
                    if h in pset:
                        natlist.append({
                            "Day": d,   # e.g. "Do."
                            "Hour": h   # e.g. "B"
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

        ## Do lunch-breaks and afternoons
        aclist = idmap["__ACTIVITIES__"]
        nosdlist = constraint_list["ConstraintMinDaysBetweenActivities"]
        if n_afternoons:
            n_ad = len(aftdays)
            agset = class_group_atoms[clid][""]
            if agset:
                kags = [f"{clid}{AG_SEP}{ag}" for ag in agset]
            else:
                kags = [clid]
            if n_afternoons < n_ad:
                n_lb = n_afternoons
                n_blocker = n_ad - n_afternoons
# I am assuming that a free afternoon requires no lunch break
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
                    aclist.append({
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
# Might also need to constrain starting time
                # lunch breaks
                for i in range(n_lb):
                    # Add activity
                    aid = str(next_activity_id())
                    aclist.append({
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
                    nosdlist.append({
                        "Weight_Percentage": "100",
                        "Consecutive_If_Same_Day": "true",
                        "Number_of_Activities": str(len(aids)),
                        "Activity_Id": aids,
                        "MinDays": "1",
                    })

        if cdata[_ForceFirstHour] == "false":
            cl_hour0_list.append({
                "Weight_Percentage": "100",
                "Max_Beginnings_At_Second_Hour": str(len(daylist)),
                "Students": clid,
                "Active": "true",
                "Comments": "",
            })

        maxlessonsperday = cdata[_MaxLessonsPerDay]
        if int(maxlessonsperday) < n_hours:
            cl_maxlessonsperday_list.append({
                # Can be < 100, but not really recommended:
                "Weight_Percentage": "100",
                "Students": clid,
                "Maximum_Hours_Daily": maxlessonsperday,
                "Active": "true",
                "Comments": "",
            })

        minlessonsperday = cdata[_MinLessonsPerDay]
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
        categories = cdata[_Categories]

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


    return constraint_list
