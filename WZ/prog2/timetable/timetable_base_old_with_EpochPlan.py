"""
timetable/timetable_base.py - last updated 2024-04-14

Build a timetable with data derived from Waldorf365.

TODO: Actually the Waldorf365 stuff should be separated out so that the
data could come from anywhere.

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
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(basedir)

#from core.base import Tr
#T = Tr("timetable.timetable_base")

### +++++

###-----


class TimetableBase:
    __slots__ = (
        "days",
        "hours",
        "teachers",
        "teacher_indexes",
        "subjects",
        "rooms",
        "room_indexes",
        "classes",
        "class_indexes",
    )

# If the data really comes from Waldorf365 using the current parsers,
# the sorting is unnecessary here, because the tables are already sorted.
# Maybe the sorting should always be done on loading ...
    def __init__(self, data):
        self.days = data.tables["DAYS"]
        self.days.sort(key = lambda x: x['#'])
        self.hours = data.tables["PERIODS"]
        self.hours.sort(key = lambda x: x['#'])
        #nslots = len(self.days) * len(self.hours)

        self.teachers = data.tables["TEACHERS"]
        #self.teachers.sort(key = lambda x: x['#'])
        self.teacher_indexes = {}
        for i, node in enumerate(self.teachers):
            #print("?teacher:", node)
            self.teacher_indexes[node["$KEY"]] = i

        self.subjects = data.tables["SUBJECTS"]
        #self.subjects.sort(key = lambda x: x['#'])

        rooms = data.tables["ROOMS"]
        ## Note that this includes virtual rooms / room groups
        #rooms.sort(key = lambda x: x['#'])
        self.rooms = []
        room_groups = []
        self.room_indexes = {}
        for node in rooms:
            try:
                rg = node["ROOM_GROUP"]
            except KeyError:
                self.room_indexes[node["$KEY"]] = len(self.rooms)
                self.rooms.append(node)
            else:
                # <rg> is a list of room keys, I need a list of room,
                # indexes, the determination of which should be postponed
                # until all rooms have been read in.
                room_groups.append((node["$KEY"], rg))
        for k, rg in room_groups:
            self.room_indexes[k] = [self.room_indexes[r] for r in rg]

        self.classes = data.tables["CLASSES"]
        #self.classes.sort(key = lambda x: x['SORTING'])
        self.class_indexes = {}
        for i, node in enumerate(self.classes):
            self.class_indexes[node["$KEY"]] = i
            #print("?class:", node)
# The divisions may or may not be named (currently if there is no name,
# "???" is used).
#TODO: Build bitmaps for all groups in the divisions, or do any other
# preparation for the collision tests.

# In classes with no divisions, the empty set of atomic groups cannot
# be used for conflict tests. If the tesing is done class-for-class, it
# could be replaced by {"*"} or all full-class activities could be
# handled separately, conflicting with anything.

            agmap = node["$GROUP_ATOMS"]
            agset = agmap[""]
            g2bits = {}
            if agset:
                i = 1
                ag2bit = {}
                # The ordering can be different each time!
                for ag in agset:
                    ag2bit[ag] = i
                    i <<= 1
                for g, ags in agmap.items():
                    b = 0
                    for ag in ags:
                        b |= ag2bit[ag]
                    g2bits[g] = b
            else:
                # The class has no divisions
                g2bits[""] = 1
            node["§GROUP_BITS"] = g2bits
            #print("?g2bits:", g2bits)

        self.read_activities(data)

#?
    def read_activities(self, data):
        """Build the activity items which are to be allocated and handle
        the fixed ones.
        """
#        next_activity_id(reset = True)


# It is possible in W365 to have courses with multiple subjects.
# It might be better to handle this by means of blocks, but the current
# (2024.04.07) support for blocks in W365 is limited.
        multisubjects = set()

#?
#        subject_activities = SubjectGroupActivities(data.full_atomic_groups)

# The weakness of block handling in W365 is causing me problems here.
# Currently I am only really supporting a single block, HU-OS. I am not
# directly recording any links between blocks and their courses (because
# this is so weak in W365 and I hope it will change ...).
# Perhaps the most promising approach would be to include both blocks
# and their members in the courses list. The blocks themselves would
# need no subjects (except the block tag and name), no teachers and no
# class-groups. The teachers and class-groups would be supplied by the
# block members. These would have no lessons, but an indication of the
# workload (Epochen or, as in W365, Epochen-Wochen) and they would
# reference the block to which they belong.
        for node in data.tables["COURSES"]:
            try:
                slist = node["SUBJECTS"]
                block = None
            except KeyError:
                sbj = node["BLOCK"]
                print("§Block:", node)

#W365
                block = node["$W365Groups"]
                if sbj not in data.sids:
                    # Invent a new subject
                    i = len(self.subjects)
                    self.subjects.append({
                        "ID": sbj,
                        "NAME": f'BLOCK: {node["NAME"]}',
                        #"#": ?
                    })
# Make it into a dict supplying the index?
                    data.sids.add(sbj)
            else:
                sbj = ",".join(data.key2node[s]["ID"] for s in slist)
                if len(slist) > 1 and sbj not in multisubjects:
                    # Invent a new subject
                    i = len(self.subjects)
                    self.subjects.append({
                        "ID": sbj,
                        "NAME": f'MULTIPLE: {sbj}',
                        #"#": ?
                    })
# Make it into a dict supplying the index?
                    multisubjects.add(sbj)
# What to do with the subject index?

        return

        if True:

            tlist = node.get("TEACHERS") or []
# How do teacher_index, room_index and class_index get in here?
            tixlist = [teacher_index[t] for t in tlist]
            gixlist = [(class_index[cx], g) for cx, g in node["GROUPS"]]
            rlist = node.get("ROOM_WISH") or []
            rixlist = [room_index[r] for r in rlist]
            ## Generate the activity or activities
            try:
                durations = node["LESSONS"]
                total_duration = sum(durations)
                # sum also works with an empty list (-> 0)
            except KeyError:
# Assume this is a block course?
                print("BLOCK COURSE?", node)
#TODO
                try:
                    master = node["MASTER"]
                except KeyError:
#TODO: This is a hack to support the weird W365 blocks in a very minimal
# way. Only one block course is epected, which will be matched up with
# this null tag.
                    master = 0
#{"TEACHERS":[98],"GROUPS":[[29,""]],"SUBJECTS":[57],"ROOM_WISH":[172],"WORKLOAD":"","BLOCK_WEEKS":"3.0"}
# This should somehow be restricted to exactly one subject
                assert len(slist) == 1
                block_courses[master].append((sbj,)) # ...

    # How are the courses and blocks linked??? Surely a block-course would
    # need a link to its block? At present I just haven't implemented this
    # because the Waldorf365 approach is so complicated. That means that the
    # block lessons (at least the fixed ones ...) can be associated with the
    # classes, but no other information is available. If teachers (etc.)
    # should be blocked by the blocks, this must be specified separately.

    # How would a "course" with no lessons look? (A bodge to cater for
    # extra workloads/payments)

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
#W365
            if block is None:
                activity["Comments"] = node["$W365ID"]
            else:
                clist = ",".join(block)
                activity["Comments"] = f'{node["$W365ID"]}+{clist}'

            for i, ll in enumerate(durations):
                if i > 0:
                    activity = activity.copy()
                    aid = str(next_activity_id())
                    activity["Id"] = aid
                    aid_list.append(aid)
                activity["Duration"] = str(ll)
#                fetlist.append(activity)
                activity_list.append(activity)
            subject_activities.add_activities(sbj, gidlist, aid_list)
        db.set_subject_activities(subject_activities)






class Timetable:
    __slots__ = (
        "timetable_base",

        "teacher_slots",
        "class_slots",
        "room_slots",
    )

    def __init__(self, timetable_base):
        self.timetable_base = timetable_base
# Would it help (cache) to use just one mega-array and slice this up?
        ## Set up the allocation arrays
        nslots = len(timetable_base.days) * len(timetable_base.hours)
        self.teacher_slots = []
        for t in timetable_base.teachers:
            self.teacher_slots.append([0] * nslots)
        # A class can have more than one activity in a slot, so lists
        # are used.
        self.class_slots = []
        for t in timetable_base.classes:
            self.class_slots.append([[] for i in range(nslots)])
        self.room_slots = []
        for t in timetable_base.rooms:
            self.room_slots.append([0] * nslots)




#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


def build_fet_file(wzdb):
    fetout = {
        "@version": FET_VERSION,
        "Mode": "Official",
        "Institution_Name": wzdb.config["SCHOOL"],
        "Comments": wzdb.scenario["$$SCENARIO"]["Id"],
    }
    fetbase = {"fet": fetout}

    days = get_days(wzdb, fetout)
    periods = get_periods(wzdb, fetout)
    get_teachers(wzdb, fetout)
    get_subjects(wzdb, fetout)
    wzdb.set_atomic_groups(get_groups(wzdb, fetout))
    fetout["Buildings_List"] = ""
    get_rooms(wzdb, fetout)
    get_activities(wzdb, fetout)

    get_time_constraints(wzdb, fetout, days, periods)

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



def get_groups(db, fetout):
    # Build a mapping of all groups (with class prefix) to
    # their "atomic" groups (also with class prefix)
    atomic_groups = {}
    # Collect class data for fet
    ylist = []
    for node in db.tables["CLASSES"]:
        #print(" ***", node)
        ylist.append(class_groups(node))

        clid = node["ID"]
        group_atoms = node["$GROUP_ATOMS"]
        ag_kag = {
            ag: f"{clid}{AG_SEP}{ag}"
            for ag in group_atoms[""]
        }
        for g, ags in group_atoms.items():
            kg = f"{clid}{AG_SEP}{g}" if g else clid
            atomic_groups[kg] = {ag_kag[ag] for ag in ags} or {clid}

    fetout["Students_List"] = {"Year": ylist}
    return atomic_groups


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

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
    #w365path = DATAPATH("test.w365", "w365_data")
    #w365path = DATAPATH("fwsb.w365", "w365_data")
    #w365path = DATAPATH("fms.w365", "w365_data")
    w365path = DATAPATH("fms_xep.w365", "w365_data")
    print("DATABASE FILE:", dbpath)
    print("W365 FILE:", w365path)
    try:
        os.remove(dbpath)
    except FileNotFoundError:
        pass

    filedata = read_active_scenario(w365path)
    w365 = W365_DB(dbpath, filedata)

    print("?????")
    for i in filedata["$$SCENARIO"]["UserConstraint"]:
        print(" ---", i)
    #quit(2)

    read_days(w365)
    read_periods(w365)
    read_groups(w365)
    read_subjects(w365)
    read_teachers(w365)
    read_rooms(w365)
    read_activities(w365)
    # Add config items to database
    w365.config2db()

    timetable_base = TimetableBase(w365)

    timetable = Timetable(timetable_base)
    #timetable.teacher_slots[1][2] = 1
    #print("§teacher_slots:", len(timetable.teacher_slots), timetable.teacher_slots)
    #timetable.class_slots[3][4].append(5)
    #print("§class_slots:", len(timetable.class_slots), timetable.class_slots)

    print("\n $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    from timetable.constraints import get_time_constraints
    get_time_constraints(w365, len(timetable_base.days), len(timetable_base.hours))


# I think I possibly need to handle only/primrily concrete absences as
# hard constraints in the primary runs. I could start with that and see
# if anything needs adding. What about the consequences of fixed lessons,
# though?
