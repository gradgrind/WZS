"""
w365/activities.py - last updated 2024-05-05

Manage data concerning the "activities" (courses, lessons, etc.).


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

from core.wzbase import Tr
T = Tr("w365.activities")

### +++++

from core.wzbase import REPORT_ERROR, REPORT_WARNING, pr_course
from w365.w365base import (
    _Course,
    _DoubleLessonMode,
    _HoursPerWeek,
#    _Teacher,
    _Shortcut,
    _Name,
#    _Firstname,
    _Id,
    _ListPosition,
    _Teachers,
    _Subjects,
    _Groups,
    _PreferredRooms,
    _Schedule,
    _Lessons,
#    _Lesson,
    _HandWorkload,
    _Fixed,
    _Day,
    _Hour,
    _EpochPlan,
    _EpochWeeks,

#    _MaxDays,
#    _MaxGapsPerDay,
#    _MaxLessonsPerDay,
#    _MinLessonsPerDay,
#    _NumberOfAfterNoonDays,
    LIST_SEP,
#    absences,
    categories,
)

### -----


def read_activities(w365_db):
    table = "COURSES"
    w365id_nodes = []
    course_lessons = {}
    block_entries = {}
    group_map = w365_db.extra["group_map"]
    for node in w365_db.scenario[_Course]:
        course_id = node[_Id]
        tlist0 = node.get(_Teachers)
        if tlist0:
            tlist = tlist0.split(LIST_SEP)
        else:
            tlist = []
        # There must be exactly one subject. Courses with multiple
        # subjects should be replaced by (defined) blocks.
        slist = node[_Subjects].split(LIST_SEP)
        sklist = [w365_db.id2key[s] for s in slist]
        if len(sklist) != 1:
            stlist = ",".join(w365_db.nodes[s]["ID"] for s in sklist)
            REPORT_ERROR(T("INVALID_SUBJECT", sbj = stlist, course = course_id))
            continue
        subject = sklist[0]
        glist = node[_Groups].split(LIST_SEP)
        _pr = node.get(_PreferredRooms)
        rlist = _pr.split(LIST_SEP) if _pr else []
        tklist = [w365_db.id2key[t] for t in tlist]
        gidlist = []
        for g in glist:
            try:
                gidlist.append(group_map[g])
            except KeyError:
                pass
        rklist = [w365_db.id2key[r] for r in rlist]
        workload = node[_HandWorkload]
        if workload == "555.555":   # (automatic!)
            workload = ""
        ## Generate the activity or activities
        # Divide lessons up according to duration
        total_duration = int(float(node[_HoursPerWeek]))
#NOTE: Not all multiple lesson possibilities are supported here.
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
        xnode = {
            "TEACHERS": tklist,
            "GROUPS": gidlist,
            "SUBJECT": subject,
            "ROOM_WISH":  rklist,
            "WORKLOAD": workload,
            "$W365ID": course_id,
        }
        cat = categories(w365_db.idmap, node)
        xnode["EXTRA"] = cat
        #print("\n???", cat)

# I suppose it is possible that constituent courses come before the
# base course of a block, so I would need to do the main handling later.
# I treat more than one "base course" as an error. If this is too severe
# a limit, one should probably extend something else!
        # Is the node connected with a block?
        try:
            b = cat.pop("Block")    # category-id of block tag
        except KeyError:
            b = None
        else:
            try:
                block_entry = block_entries[b]
            except KeyError:
                block_entry = [None, []]
                block_entries[b] = block_entry
        epweeks = node[_EpochWeeks]
        if total_duration == 0:
            if epweeks != "0.0":
                # Block ("Epoche")
                if not b:
#TODO: Maybe this should be an error?
                    REPORT_WARNING(f"Epoche ohne Kennzeichen: {pr_course(w365_db, xnode)}")
                xnode["BLOCK_WEEKS"] = epweeks
            if b:
                block_entry[1].append(xnode)
                # Don't immediately add block members to the database,
                # wait until the block-base-course keys are available,
                # so that a link can be included.
                continue
        elif epweeks != "0.0":
#TODO
            REPORT_ERROR(f"Kurs mit Epochen- und Stundenanteil: {pr_course(w365_db, xnode)}")
            continue    # ignore this entry!
        else:
            if b:
                if block_entry[0]:
                    REPORT_ERROR(f"Epochenschiene {w365_db.idmap[b]} hat zwei Kurse mit Stunden")
                    continue    # ignore this entry!
                block_entry[0] = xnode
            xnode["LESSONS"] = lessons
            course_lessons[course_id] = []

        #print("§XNODE:", xnode)
        w365id_nodes.append((course_id, xnode))
    # Add to database
    w365_db.add_nodes(table, w365id_nodes)
    # Add block members
    w365id_nodes.clear()
    for b, v in block_entries.items():
        n0, mlist = v
        k = w365_db.id2key[n0["$W365ID"]]
        #print("\n%%%%%%%%%%", k, b)
        n0["$MEMBERS"] = mlist
        for n in mlist:
            n["BLOCK_ROOT"] = k
            #print(" ++", n)
            # In member courses the W365 course-id is not needed
            w365id_nodes.append((n.pop("$W365ID"), n))
        #print("\n%%%%%%%%%%", n0)
    # Add to database
    w365_db.add_nodes(table, w365id_nodes)

#TODO: Need to specify which "Schedule" to use
    schedules = [
        (float(node[_ListPosition]), node[_Name], node[_Lessons])
        for node in w365_db.scenario[_Schedule]
    ]
    schedules.sort()
    #for _, n, _ in schedules:
    #    print(" +++", n)

# The "Vorlage" might have only fixed lessons.
# If adding or deleting lessons, the Lessons field of the Schedule
# must be updated, or a new Schedule must be built (maybe better).

#TODO: Assume the last schedule?
    isched = -1
# or the first?
    isched = 0
    lesson_ids = schedules[isched][-1].split(LIST_SEP)
    lesson_set = set(lesson_ids)
# (or maybe rather one with a particular name?)

#TODO?
#    w365_db.w365lessons = lesson_ids

# My current preference is to ignore the W365 Epochen, using tagged
# "normal" courses instead.

    for lid in lesson_ids:
        node = w365_db.idmap[lid]
        try:
            course_id = node[_Course]
        except KeyError:
#TODO
            REPORT_WARNING("Zeiten für Epochenschienen werden nicht berücksichtigt")
            continue
        if node[_Fixed] == "true":
            slot = (node[_Day], node[_Hour])
        else:
            slot = None
        # Add lesson id and time slot (if fixed) to course
        course_lessons[course_id].append((lid, slot))

    # Now deal with the individual lessons
    w365id_nodes.clear()
    for course_id, lslots in course_lessons.items():
        if lslots:
            lesson_times = set()
            for l_id, slot in lslots:
                #print("    ", l_id, slot)
                if slot:
                    lesson_times.add(slot)
            pltimes = process_lesson_times(lesson_times)
            #print(" --c--:", pltimes)
            k = w365_db.id2key[course_id]
            for ll, tlist in pltimes.items():
                for d, p in tlist:
                    xnode =  {
                        "LENGTH": str(ll),
                        "_Course": k,
                        "DAY": str(d),
                        "PERIOD": str(p),
                        "FIXED": "true",
                        #"_Parallel": 0,
                    }
                    w365id_nodes.append(("", xnode))
                    #print("     ++", xnode)
    # Add to database
    w365_db.add_nodes("LESSONS", w365id_nodes)
#TODO: Note that if I am only including "fixed" lessons, I don't need
# them to have a "FIXED" field!


#TODO: Might want to record the ids of non-fixed lessons as these entries
# might get changed? Actually, probably not, because I will probably
# generate a new Schedule.

# Do I need the EpochPlan to discover which teachers are involved in an
# Epoch, or can I get it from the Course entries somehow? No, this is really
# not ideal. There is a tenuous connection between "Epochenschienen" and
# courses only when an "Epochenplan" has been generated: there are then
# lessons which point to the course. Maybe for now I should collect the block
# times associated with the classes (I suppose using the EpochPlan to
# identify the classes is best? – it also supplies the name tag), then
# go through the block courses to find those in a block (test EpochWeeks?)
# and hence any other infos ... especially the teachers, I suppose.

# Für jede Klasse, die an einer Epoche beteiligt ist, gibt es einen Satz
# "Lessons", die identische Zeiten angeben. So entstehen viele überflüssige
# Einträge – es wäre besser, die "Lessons" mit der Epochen zu verknüpfen,
# einmalig.


#TODO: Might want to represent the Epochs as single course items in fet?
# That would be necessary if the teachers are included (but consider also
# the possibility of being involved in other Epochen (e.g. Mittelstufe),
# which might be different ... That's difficult to handle anyway.
# Perhaps it's easier to put no teachers in and block the teachers
# concerned in "Absences"?


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


#TODO: Consider how to ensure that two lessons of a course do not
# end up on the same day. One possibility would be to look for group
# intersections at the "atomic" level, but it should also be possible
# to seek the intersections within a class division, as it is very
# likely that the divisions in a single subject will all lie within
# a single division (e.g. 10, 10.A and 10.B: 10.A and 10.B can have a
# subject on the same day, but other combinations are not allowed).
