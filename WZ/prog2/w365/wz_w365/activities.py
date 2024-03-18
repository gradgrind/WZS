"""
w365/wz_w365/actiities.py - last updated 2024-03-18

Manage data concerning the "activities" (courses, lessons, etc.=.

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
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(basedir)

#from core.base import Tr
#T = Tr("w365.wz_w365.activities")

### +++++

from w365.wz_w365.w365base import (
    W365_DB,
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


#TODO
def read_activities(w365_db):
    table = "ACTIVITIES"
    w365id_nodes = []

    multisubjects = set()
    course2activities = {}

#    subject_activities = SubjectGroupActivities(idmap["__CLASS_GROUP_ATOMS__"])
#?
    course_lessons = {}

#?
    group_map = w365_db.group_map
    for node in w365_db.scenario[_Course]:
        course_id = node[_Id]
        tlist = node[_Teachers].split(LIST_SEP)
        slist = node[_Subjects].split(LIST_SEP)
        glist = node[_Groups].split(LIST_SEP)
        _pr = node.get(_PreferredRooms)
        rlist = _pr.split(LIST_SEP) if _pr else []
#TODO: What internal forms do I want and what needs to be prepared for
# the database?
        tklist = [w365_db.id2key[t] for t in tlist]
        gidlist = [group_map[g] for g in glist]
        sklist = [w365_db.id2key[s] for s in slist]
        rklist = [w365_db.id2key[r] for r in rlist]
#TODO: rooms?

        workload = node[_HandWorkload]
        if workload == "555.555":   # (automatic!)
            workload = ""

        ## Generate the activity or activities
        # Divide lessons up according to duration
        total_duration = int(float(node[_HoursPerWeek]))
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
        xnode = {
            "TEACHERS": tklist,
            "GROUPS": gidlist,
            "SUBJECTS": sklist,
            "ROOM_WISH":  rklist,
            "WORKLOAD": workload,
        }
        if total_duration == 0:
            # Block ("Epoche")
            xnode["BLOCK_WEEKS"] = node[_EpochWeeks]
        else:
            xnode["LESSONS"] = lessons
            course_lessons[course_id] = []
        print("§XNODE:", xnode)
        w365id_nodes.append((course_id, xnode))
        c = categories(w365_db.idmap, node)
        if c:
            xnode["$$EXTRA"] = c
    # Add to database
    w365_db.add_nodes(table, w365id_nodes)

#--------------------------------------------------------------------
#TODO: the blocks ("Epochen") must be handled separately (at present).

#TODO: Need to specify which "Schedule" to use
    schedules = [
        (float(node[_ListPosition]), node[_Name], node[_Lessons])
        for node in w365_db.scenario[_Schedule]
    ]
    schedules.sort()
    for _, n, _ in schedules:
        print(" +++", n)

# The "Vorlage" might have only fixed lessons.
# If adding or deleting lessons, the Lessons field of the Schedule
# must be updated, or a new Schedule must be built (maybe better).

#TODO: Assume the last schedule?
    isched = -1
# or the first?
    isched = 0
    lesson_ids = schedules[isched][-1].split(LIST_SEP)
    lesson_set = set(lesson_ids)
#?
    w365_db.w365lessons = lesson_ids
# Maybe rather one with a particular name?

    print("\n ****** LESSONS:")

    block_lessons = {}
    for ep in w365_db.scenario[_EpochPlan]:
        print("????ep:", ep)
        block_lessons[ep[_Id]] = []

    # NOTE that I am only picking up fixed Epochenstunden ...
#TODO: Non-fixed ones cannot at present be forced to be double lessons,
# so their use is a bit limited.
    for lid in lesson_ids:
        node = w365_db.idmap[lid]
        course_id = node.get(_Course)
#        course_key = w365_db.id2key[course_id]
        if node[_Fixed] == "true":
            slot = (node[_Day], node[_Hour])
        else:
            slot = None
        if course_id:
            # Add lesson id and time slot (if fixed) to course
            course_lessons[course_id].append((lid, slot))
        else:
            ep_id = node[_EpochPlan]
            block_lessons[ep_id].append((lid, slot))

    w365id_nodes.clear()
    ep_times = {}
    for ep_id, epl in block_lessons.items():
        print("????ep_id:", ep_id)
        lesson_times = set()
        for l_id, slot in epl:
            print("    ", l_id, slot)
            if slot:
                lesson_times.add(slot)
        if lesson_times:
            node = w365_db.idmap[ep_id]
            cl_list = [
                w365_db.group_map[_id]
                for _id in node[_Groups].split(LIST_SEP)
            ]
# I think only whole classes are permitted in "Epochen", so I could drop
# the groups (but see previous use of "GROUPS" field and consider
# future changes).
#        print("    or just classes:", [cl for cl, _ in cl_list])
            print(" -e-", node, lesson_times)
            pltimes = process_lesson_times(lesson_times)
            llengths = []
            ltlist = []
            for ll, times in pltimes.items():
                for d, p in times:
                    llengths.append(ll)
                    ltlist.append((ll, d, p))
            ep_times[ep_id] = ltlist
            xnode = {
#            "TEACHERS": tklist,
                "GROUPS": cl_list,
#            "SUBJECTS": sklist,
#            "ROOM_WISH":  rklist,
                "BLOCK": node[_Shortcut],
                "NAME": node[_Name],
                "LESSONS": llengths,
#            "WORKLOAD": workload,
            }
# Field "ID"?
            print("§XNODE:", xnode)
            w365id_nodes.append((ep_id, xnode))

#TODO: convert to a more convenient form (see <process_lesson_times>)
# and add to the groups covered by the block. If a group already has
# block times, that would be treated as an error (current limit of one
# block per class).

# At present it seems best not to attempt to deal with "Epochen" for which
# no times are set. It is all too complicated. Also more than one "Epoche"
# in a class may theoretically sort-of work, but if that is true, then it
# is not useable in practice.

    # Add to database
    w365_db.add_nodes(table, w365id_nodes)

#TODO
    w365id_nodes.clear()

    for ep_id, ltlist in ep_times.items():
        k = w365_db.id2key[ep_id]
        for ll, d, p in ltlist:
            xnode =  {
                "LENGTH": str(ll),
                "_Course": k,
                "DAY": str(d),
                "PERIOD": str(p),
                "FIXED": "true",
                #"_Parallel": 0,
            }
            w365id_nodes.append(("", xnode))
            print("     ++", xnode)
    for course_id, lslots in course_lessons.items():
        if lslots:
            lesson_times = set()
            for l_id, slot in lslots:
                #print("    ", l_id, slot)
                if slot:
                    lesson_times.add(slot)
            pltimes = process_lesson_times(lesson_times)
            print(" --c--:", pltimes)
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
                    print("     ++", xnode)
    # Add to database
    w365_db.add_nodes("LESSONS", w365id_nodes)
    return


#TODO: Might want to record the ids of non-fixed lessons as these entries
# might get changed? Actually, probably not, because I will probably
# generate a new Schedule.

# Do I need the EpochPlan to discover which teachers are involved in an
# Epoch, or can I get it from the Course entries somehow? No, this is really
# not ideal. There is a tenuous connection between Epochenschienen and courses
# only when an Epochenplan has been generated: there are then lessons
# which point to the course. Maybe for now I should collect the block
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


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

# Remove existing database file, add basic data and activities from w365.

from w365.wz_w365.rooms import read_rooms
from w365.wz_w365.subjects import read_subjects
from w365.wz_w365.teachers import read_teachers
from w365.wz_w365.class_groups import read_groups


if __name__ == "__main__":
    from core.base import DATAPATH
    from w365.wz_w365.w365base import read_active_scenario

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

    read_groups(w365)
    read_subjects(w365)
    read_teachers(w365)
    read_rooms(w365)
    read_activities(w365)
