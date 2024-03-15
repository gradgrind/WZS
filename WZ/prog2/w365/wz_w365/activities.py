"""
w365/wz_w365/actiities.py - last updated 2024-03-13

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
#    _Teacher,
    _Shortcut,
    _Name,
#    _Firstname,
    _Id,
    _Teachers,
    _Subjects,
    _Groups,
    _PreferredRooms,

#    _MaxDays,
#    _MaxGapsPerDay,
#    _MaxLessonsPerDay,
#    _MinLessonsPerDay,
#    _NumberOfAfterNoonDays,
    LIST_SEP,
#    absences,
#    categories,
)

### -----

#    $dbkey2node: db-rowid -> xnode
#    $$id2dbkey: w365-id -> db-rowid

#TODO
def read_activities(datamap):
    scenario = datamap["$$SCENARIO"]
    idmap = datamap["$$IDMAP"]
    id2dbkey = datamap["$$id2dbkey"]
    nodedata = {}
    datamap["ACTIVITIES"] = nodedata


#    id2node = {}
#    nodedata["$$id2node"] = id2node
    for node in scenario[_Course]:



        id = node[_Shortcut]
        xnode = {
            "ID": id,
            "LASTNAME": node[_Name],
            "FIRSTNAMES": node[_Firstname],
        }
        id2node[node[_Id]] = xnode
        nodedata[id] = xnode
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
        xnode["$$CONSTRAINTS"] = constraints
        a = absences(idmap, node)
        if a:
            xnode["NOT_AVAILABLE"] = a
        c = categories(idmap, node)
        if c:
            xnode["$$EXTRA"] = c



# Note that at present the blocks ("Epochen") must be handled separately.

def get_activities(idmap, fetout, scenario):

#TODO: Perhaps the id2node references should point not to the w365 node,
# but be the rowid of the database entry? There would also need to
# be a mapping from these to the actual data.

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
#TODO: What internal forms do I want and what needs to be prepared for
# the database?
        tklist = [id2dbkey[t] for t in tlist]
#?
        gidlist = [id2group[g] for g in glist]
#?
        sbj = ",".join(id2subject[s][0] for s in slist)
        if len(slist) > 1 and sbj not in multisubjects:
            # Invent a new subject
            sbjlist = fetout["Subjects_List"]["Subject"]
            sbjlist.append({"Name": sbj, "Comments": f"MULTI_{sbj}"})
            multisubjects.add(sbj)

        rklist = [id2dbkey[r] for r in rlist]
#TODO: rooms

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

    idmap["__ACTIVITIES__"] = fetlist





# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

# Remove existing database file, add teachers from w365.

if __name__ == "__main__":
    from core.base import DATAPATH
    from w365.wz_w365.w365base import read_active_scenario, create_db

    dbpath = DATAPATH("db365.sqlite", "w365_data")
    w365path = DATAPATH("test.w365", "w365_data")
    print("DATABASE FILE:", dbpath)
    print("W365 FILE:", w365path)
    try:
        os.remove(dbpath)
    except FileNotFoundError:
        pass

    filedata = read_active_scenario(w365path)

    read_teachers(filedata)

    create_db(dbpath, filedata)
