"""
timetable/constraints.py - last updated 2024-04-09

Prepare constraints for activity allocation.


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

#TODO: pretty well everything ...

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
from w365.wz_w365.class_groups import AG_SEP

#TODO: There could be a clash between the current implementation of
# lunch breaks and the max-gaps settings.

#TODO: Note that it might be better to not implement stuff like
# "max. afternoons" directly, but rather to do multiple runs with
# different fixed afternoons. This might also make dealing with lunch
# breaks easier.

def EXTRA_SUBJECTS():
    return [
        {"Name": SUBJECT_LUNCH_BREAK, "Comments": "Mittagspause"},
        {"Name": SUBJECT_FREE_AFTERNOON, "Comments": "Freier Nachmittag"}
    ]

def collect_teacher_constraints(constraints, n_days):
    """Process Waldorf365 teacher constraints.
    """
    absence_list = []           # not-available times
    max_days_list = []          # max days per week
    maxlessonsperday_list = []  # max lesson periods per day
    maxgapsperday_list = []     # max gaps per day
    minlessonsperday_list = []  # min lesson periods per day
    afternoon_list = []         # max teaching afternoons

#    return
#?
    for node in d.tables["TEACHERS"]:
#        if tid not in used:
#            continue
# ...
        tid = node["ID"]
        cdata = node["$$CONSTRAINTS"]


#!
        n_afternoons = int(constraints[_NumberOfAfterNoonDays])

# Maybe rather start with the explicitly declared absences and see if
# these already cover the free afternoons according to max-afternoons.
# But the max-afternoons is perhaps a soft constraint so all that could
# happen is that it might be rendered superfluous. However, a hard
# max-afternoons might also be useful, when it doesn't really matter
# which afternoons are chosen. Is a weighting available from W365? No,
# none of the constraints in the teacher node have a weighting.
# Maybe support hard and soft, choosing on the basis of the weighting,
# or only support the soft constraint but allow a large penalty.
# If "0" afternoons is set this should be set as absence, not as
# an additional constraint here? But is it really a hard constraint?
# Suggestion: Make the max-afternoons soft, the weighting would be a
# global value (settable default). Possibly W365 has a means to set this
# default. Another source might be able to set individual weightings.

        # Check necessity for (soft) constraint
        n_free = n_days
        for dhours in node.get("NOT_AVAILABLE"):
            if afternoon_set.issubset(dhours):
                n_free -= 1
        if n_free >  n_afternoons:
            pass
#TODO: add soft constraint with weighting (where would this be?),
# or default weighting (where?)



        absences = {}

#TODO: This could lead to some tricky constraint interactions!
# If there are fixed absences, the constraints could depend on exactly
# which days are chosen – which, could be a big problem ...
# Perhaps I should choose the days with the most free slots?
# Actually, teachers can (mostly) be a bit more flexible than classes, so
# perhaps the initial approach could work for them.

#!
        maxdays = constraints[_MaxDays]
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
#        categories = cdata[_Categories]

    constraint_list["ConstraintTeacherIntervalMaxDaysPerWeek"] = t_afternoon_list
    constraint_list["ConstraintTeacherNotAvailableTimes"] = t_absence_list
    constraint_list["ConstraintTeacherMaxDaysPerWeek"] = t_max_days_list
    constraint_list["ConstraintTeacherMaxHoursDaily"] = t_maxlessonsperday_list
    constraint_list["ConstraintTeacherMaxGapsPerDay"] = t_maxgapsperday_list
    constraint_list["ConstraintTeacherMinHoursDaily"] = t_minlessonsperday_list




def get_time_constraints(data, ndays, nhours):
    not_on_same_day_list = []
    afternoon_start = data.config["AFTERNOON_START_PERIOD"]
    if afternoon_start >= 0:
        afternoon_hours = {i for i in range(afternoon_start, nhours)}
    else:
        afternoon_hours = set()
    lunchbreak = data.config["LUNCHBREAK"] # list of period indexes (ints, not tags)
#?
    lunchbreak_hours = set(lunchbreak)
    print("§lb", lunchbreak_hours)
    print("§pm", afternoon_hours)

    return

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


# The specifically W365 bits should be encapsulated in a module which
# is then used before the main timetable stuff to pre-process the info.
# It could then be presented to the timetable handler as CONSTRAINTS,
# for example, replacing $$CONSTRAINTS. Actually this could/should be
# done before storing to the datase.
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
#        if tid not in used:
#            continue
# ...
        tid = node["ID"]
        cdata = node["$$CONSTRAINTS"]
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
        if n_maxdays > n_days:
            n_maxdays = n_days
        if n_afternoons < n_maxdays:
#? afternoon_start? afternoon_hours (set!)?
            assert afternoon_start >= 0
            if n_afternoons == 0:
                for d in range(n_days):
                    absences[d] = afternoon_hours.copy()
        else:
#?
            n_afternoons = -1

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
        cdata = node["$$CONSTRAINTS"]
#TODO!!!!! Could there be a filter for classes with too few subjects?
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
        categories = node.get("$$EXTRA")
        if categories:
            print("$$EXTRA:", categories)

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
