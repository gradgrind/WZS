"""
timetable/tt_basic_data.py

Last updated:  2023-09-17

Handle the basic information for timetable display and processing.


=+LICENCE=============================
Copyright 2023 Michael Towers

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

=-LICENCE========================================
"""

if __name__ == "__main__":
    import sys, os
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import start
    start.setup(os.path.join(basedir, 'TESTDATA'))

T = TRANSLATIONS("timetable.tt_basic_data")

### +++++

from typing import NamedTuple, Optional

from core.basic_data import (
    get_days,
    get_periods,
    get_classes,
    get_teachers,
    get_rooms,
    NO_CLASS,
    GROUP_ALL,
    NO_TEACHER
)
from core.db_access import db_select, db_query, db_read_fields

class COURSE_INFO(NamedTuple):
    klass: str
    group: str
    sid: str
    tid: str
    bsid: str
    room: str

class ACTIVITY_GROUP(NamedTuple):
    teacher_set: set[int]
    classgroup_set: set[int]
    courses: list[COURSE_INFO]
    fixed_rooms: list[int]
    room_choices: list[list[int]]

class TT_LESSON(NamedTuple):
    index: int
    teachers: list[int]
    classgroups: list[int]
    fixed_rooms: list[int]
    room_choices: list[list[int]]
    courselist: list[COURSE_INFO]
    lesson_id: int
    subject_tag: str
    length: int
    lesson_group: int
    time: int
    # These are only needed for initialisation
#TODO: Consider moving the following out of this data structure
    placement0: int
    rooms0: list[int]

### -----


def get_teacher_indexes():
    """Each teacher gets a unique index, so that integers can be used
    instead of the tag (str) in speed critical code. Index 0 is reserved
    for the null teacher (<NO_TEACHER>), the others follow contiguously.
    """
    timap = {NO_TEACHER: 0}
    i = 0
    for tid in get_teachers().list_teachers():
        if tid != NO_TEACHER:
            i += 1
            timap[tid] = i
    return timap


def get_room_map():
    """Each room gets a unique index, so that integers can be used
    instead of the tag (str) in speed critical code.
    """
    rmap = {"": 0}
    i = 0
    for r, n in get_rooms():
        i += 1
        rmap[r] = i
    return rmap


def get_room_groups():
    rgroups = {}
    for rg, rid in db_read_fields("TT_ROOM_GROUPS", ("ROOM_GROUP", "RID")):
        try:
            rgroups[rg].append(rid)
        except KeyError:
            rgroups[rg] = [rid]
    return rgroups


def get_lg_lessons():
    """Each lesson-group will have one or more classes (though the null
    class is possible, too) and one or more teachers (though the null
    teacher is possible, too).
    """
    q = """select

        Lesson_group,
        Lid,
        LENGTH,
        TIME,
        PLACEMENT,
        ROOMS

        from LESSONS

        where Lesson_group != '0'
    """
    lg_ll = {}
    for r in db_query(q):
        lg = r.pop(0)
        try:
            lg_ll[lg].append(r)
        except KeyError:
            lg_ll[lg] = [r]
    return lg_ll


def simplify_room_lists(roomlists: list[list[int]]
) -> Optional[tuple[list[int], list[list[int]]]]:
    """Simplify room lists, where possible, and check for room conflicts.

    The basic room specifications for the individual "tlessons" are
    processed into compulsory single rooms and further required rooms
    which can be one of a number of choices.
    This approach is in some respects not ideal, but given the
    difficulties of specifying concisely the room requirements for
    blocks containing multiple courses, it seemed a reasonable compromise.

    <roomlists>: A list of lists. Each entry in the outer list
        corresponds to one required room. Such an entry is a list
        containing the indexes of the permissible rooms.

    Return:
        List of required rooms (indexes) where there is no choice.
        List of choice lists.

    A <None> return value indicates invalid data.
    """
    ## Collect single room "choices" and remove redundant entries
    srooms = set()      # (single) fixed room
    rooms = []          # room choice list
    for rchoice in roomlists:
        if len(rchoice) == 1:
            r = rchoice[0]
            if r in srooms:
                return None     # Internal conflict!
            srooms.add(r)
        else:
            rooms.append(rchoice)
    # Filter already-claimed rooms from the choice lists, but retain
    # ordering of choices
    i = 0
    while i < len(rooms):
        rl = rooms[i]
        for r in srooms.intersection(rl):
            rl.remove(r)
        if rl:
            if len(rl) == 1:
                # new single room
                srooms.add(rl[0])
                del rooms[i]
                i = 0
            else:
                i += 1
        else:
            return None     # No rooms left, internal conflict!
    # Sort according to list length
    rooms.sort(key=len)
    return (list(srooms), rooms)


class TimetableData:
    __slots__ = (
        "periods_per_day", #: int
        "days_per_week", #: int
        "group_division", #: dict[str, tuple[ # key: class
        #     list[list[str]], # list of primary groups in each division
        #     dict[str, tuple[ # key: group (also '*')
        #         int,      # division index (-1 for '*')
        #         list[str] # list of primary groups
        #     ]]
        # ]]
        # The "groups" are all groups which can be used in specifying a
        # "course". "Divisions" comprise "primary groups". These are
        # also "groups", i.e. they can be used in specifying courses.
        # The difference is that a "group" can comprise more than one
        # "primary group" from a single division.
        # The undivided class ('*') is not considered to be a division,
        # it has the "index" -1 and contains no primary groups.
        "class_room", #: dict[str, str]
        "class_group_atoms", #: dict[str, dict[str, list[int]]]
        "n_class_group_atoms", #: int
        # <n_class_group_atoms> is provided because <class_group_atoms>
        # (being a dict of dicts) doesn't directly provide the needed number.
        "teacher_index", #: dict[str, int]
        "room_index", #: dict[str, int]
        "room_groups", #: dict[str, list[int]]
        "tt_lessons", #: list[TT_LESSON]
        "class_ttls", #: dict[str, list[int]] (class -> index to <tt_lessons>)
        "teacher_ttls", #: dict[list[int]] (tid -> index to <tt_lessons>)
    )

    def period2day_period(self, px):
        return divmod(px - 1, self.periods_per_day)

    def __init__(self):
        ## Each atomic group within a class gets a unique index.
        ## The groups need to be mapped to a list of these indexes.
        ## The groups within each division are also collected.
        c_rmap = {}     # { class: classroom }
        c_g_map = {}    # { class: { group: [ index, ... ] } }
        # The NO_CLASS entry might be superfluous: there shouldn't be
        # any entries with a non-null group in the null class.
        c_g_map[NO_CLASS] = {GROUP_ALL: [0]}
        cgi = 0     # Maximum index in <c_g_map>, i.e. number of atomic
                    # groups (valid indexing starts at 1)
        group_division = {} # { class: }
        for klass, cdata in get_classes().items():
            #print("?", klass)
            c_rmap[klass] = cdata.classroom
            if klass != NO_CLASS:
                cg = cdata.divisions
                ## Build group-division map
                divs = cg.divisions
#TODO: GROUP_ALL is not a list ... would an empty one do?
                g2div = {GROUP_ALL: (-1, GROUP_ALL)}
#                                        =========
                dlist = []
                group_division[klass] = (dlist, g2div)
                for i, div in enumerate(divs):
                    dgas = []
                    for d, v in div:
                        if v is None:
                            dgas.append(d)
                            g2div[d] = (i, [d])
                        else:
                            g2div[d] = (i, v)
                    dlist.append(dgas)
                ## Build atomic group map
                gmap = {}
                c_g_map[klass] = gmap
                amap = {}
                for ag in cg.atomic_groups:
                    cgi += 1
                    amap[ag] = cgi
                for g, ags in cg.group_atoms().items():
                    #print("???", g, ags)
                    gmap[g] = [amap[ag] for ag in ags]
                if gmap:
                    gmap[GROUP_ALL] = list(amap.values())
                else:
                    cgi += 1
                    gmap[GROUP_ALL] = [cgi]
                #print("  gmap:", gmap)
        self.group_division = group_division
        self.class_room = c_rmap
        self.class_group_atoms = c_g_map
        self.n_class_group_atoms = cgi
        self.teacher_index = get_teacher_indexes()
        rimap = get_room_map()
        self.room_index = rimap
        self.room_groups = {
            rg: [rimap[r] for r in rl]
            for rg, rl in get_room_groups().items()
        }
        lg_map = self.get_activity_groups()
        lg_ll = get_lg_lessons()
#        self.collate_lessons(lg_ll, lg_map, rimap)

        ## Combine the data for the lesson groups and the individual
        ## lessons to a list of TT_LESSON items.
        ## For more effective placement checks teachers, groups and
        ## rooms are replaced by integers (there is a somewhat dynamic
        ## correspondence of the various tags to the indexes, which may
        ## vary from run to run).
        ## Information from the "courses" connected with such an item is
        ## retained as a list with the original values, not the numeric
        ## equivalents.

        # The following is for converting lesson "times" to week-vector
        # indexes:
        days = get_days()
        day2index = days.index
        self.days_per_week = len(days)
        periods = get_periods()
        nperiods = len(periods)
        self.periods_per_day = nperiods
        period2index = periods.index
        # Run through the lesson groups and their associated lessons
        tt_lessons = [None]
        class_activities = {}       # class -> list of tt_lesson indexes
        teacher_activities = {}     # teacher -> list of tt_lesson indexes
        for lg, ll in lg_ll.items():
            ag = lg_map[lg]
            tlist = sorted(ag.teacher_set)
            cglist = sorted(ag.classgroup_set)
            tids = set()
            classes = set()
            sid0, bsid0 = None, None
            for course in ag.courses:
                # Each row <courselist> must have the same bsid and, if
                # bsid is null, the same sid.
                # <sid0> will be the lesson subject.
                bsid = course.bsid
                sid = course.sid
                if bsid != bsid0:
                    assert bsid0 is None
                    bsid0 = bsid
                    if bsid0:
                        sid0 = bsid0
                    else:
                        sid0 = sid
                elif not bsid:
                    assert sid == sid0
                # Extend teacher and class lists
                tid = course.tid
                assert tid
                if tid != NO_TEACHER:
                    tids.add(tid)
                klass = course.klass
                assert klass
                if klass != NO_CLASS and course.group:
                    classes.add(klass)
            for lid, l, t, p0, rr0 in ll:
                tt_index = len(tt_lessons)
                for tid in tids:
                    try:
                        teacher_activities[tid].append(tt_index)
                    except KeyError:
                        teacher_activities[tid] = [tt_index]
                for klass in classes:
                    try:
                        class_activities[klass].append(tt_index)
                    except KeyError:
                        class_activities[klass] = [tt_index]
                if t:
#TODO: What if it is a reference (starting with "^")?
                    d, p = t.split(".")
                    t_index = day2index(d) * nperiods + period2index(p) + 1
                else:
                    t_index = 0
#TODO: Consider moving p0 and rr0 out of this data structure
                if p0:
                    d, p = p0.split(".")
                    p0_index = day2index(d) * nperiods + period2index(p) + 1
                else:
                    p0_index = 0
                if rr0:
                    rplist = [rimap[r] for r in rr0.split(",")]
                else:
                    rplist = []
                tt_lessons.append(TT_LESSON(
                    tt_index,
                    tlist,
                    cglist,
                    ag.fixed_rooms,
                    ag.room_choices,
                    ag.courses,
                    lid,
                    sid0,
                    l,
                    lg,
                    t_index,
                    p0_index,
                    rplist
                ))
        self.tt_lessons = tt_lessons
        self.class_ttls = class_activities
        self.teacher_ttls = teacher_activities

    def get_activity_groups(self):
        """Return a mapping of "activity groups" – that is, a collection
        of data for each non-null Lesson_group value.
        """
        q = """select

            Lesson_group,
            --Lesson_data,
            CLASS,
            GRP,
            SUBJECT,
            TEACHER,
            BLOCK_SID,
            --BLOCK_TAG,
            ROOM

            from COURSE_LESSONS
            inner join COURSES using (Course)
            inner join LESSON_GROUPS using (Lesson_group)
            inner join LESSON_DATA using (Lesson_data)

            where Lesson_group != '0'
        """
        lg_map = {}
        r_map = self.room_index
        t_map = self.teacher_index
        for rec in db_select(q):
            lg = rec["Lesson_group"]
            klass = rec["CLASS"]
            rm = self.class_room[klass]
            if rm:
                room = rec["ROOM"].replace("$", rm)
            else:
                room = rec["ROOM"]
                assert "$" not in room
            group = rec["GRP"]
            sid = rec["SUBJECT"]
            bsid = rec["BLOCK_SID"]
            tid = rec ["TEACHER"]
            row = COURSE_INFO(
                klass,
                group,
                sid,
                tid,
                bsid,
                room
            )
            cgalist = self.class_group_atoms[klass][group] if group else []
            ti = t_map[tid]
            try:
                lg_data = lg_map[lg]
                if ti:
                    lg_data[0].add(ti)
                if cgalist:
                    lg_data[1].update(cgalist)
                lg_data[2].append(row)
                if room:
                    lg_data[3].add(room)
            except KeyError:
                lg_map[lg] = (
                    {ti} if ti else set(),
                    set(cgalist),
                    [row],
                    {room} if room else set()
                )
        agmap = {}
        for lg, lg_data in lg_map.items():
            rsl = []
            for rx in lg_data[3]:
                try:
                    rsl.append(self.room_split(rx))
                except KeyError:
                    cdata = lg_data[2][0]
                    sbj = cdata.bsid or cdata.sid
                    cstr = f"{cdata.klass}.{cdata.group},{cdata.tid},{sbj}"
                    if len(lg_data[2]) > 1:
                        cstr += " ..."
                    REPORT(
                        "ERROR",
                        T["UNKNOWN_ROOM_GROUP"].format(
                            course = cstr,
                            rooms = rx,
                        )
                    )
            srl = simplify_room_lists(rsl)
            #print("???", rsl)
            #print("   -->", srl)
            if not srl:
                cdata = lg_data[2][0]
                sbj = cdata.bsid or cdata.sid
                cstr = f"{cdata.klass}.{cdata.group},{cdata.tid},{sbj} ..."
                assert len(lg_data[2]) > 1
                # I think an error can only occur when there are
                # multiple courses, so the assertion is a check.
                REPORT(
                    "ERROR",
                    T["ROOM_ERROR"].format(
                        course = cstr,
                        rooms = ", ".join(lg_data[3]),
                    )
                )
                srl = ([], [])
            agmap[lg] = ACTIVITY_GROUP(*lg_data[:3], *srl)
        return agmap

    def room_split(self, room_choice: str) -> list[int]:
        """Split a room (choice) string into components.
        If there is a '+', it must be followed by a valid room-group
        name, not preceded by a '/', and be the last item in the string.
        The group is replaced by its contents, though rooms are not
        included more than once in the resulting list.
        The rooms are returned as indexes.
        """
        rs = room_choice.split('+')
        if len(rs) == 1:
            rgl = []
        else:
            room_choice, rg = rs            # ValueError if not 2 items
            rgl = self.room_groups[rg]      # KeyError if invalid
        if room_choice:
            r_map = self.room_index
            rl = [r_map[r] for r in room_choice.split('/')]
        else:
            rl = []
        for rx in rgl:
            if rx not in rl:
                rl.append(rx)
        return rl


#TODO: This is the version for "3a", using the PARALLEL_LESSONS table.
# A future version might integrate the info into the LESSONS table.
def get_parallels():
    q = """select

        TAG,
        Lesson_id,
        WEIGHTING

        from PARALLEL_LESSONS

        --where WEIGHTING = '+'
    """
    pmap = {}
    for row in db_query(q):
        tag, lid, w = row
        try:
            ll, w0 = pmap[tag]
            ll.append(lid)
#TODO: ...
            if w != w0:
                print(f"WARNING: // weight mismatch for {tag}: {ll} – '{w0}' vs '{w}'")

                # Take the smaller weight
                if w != '+' and (w0 == '+' or w < w0):
                    pmap[tag][1] = w

        except KeyError:
            pmap[tag] = [[lid], w]

#TODO: ... check > 1 lids
    for tag, ll in pmap.items():
        if len(ll) < 2:
            print(f"WARNING: // missing lesson for {tag}: {ll}")
    return pmap


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from core.db_access import open_database
    open_database()

    print("\n ROOM GROUPS")
    for rg, rlist in get_room_groups().items():
        print(f"  -- {rg:10}", rlist)

    tt_data = TimetableData()

    print("\n TEACHER INDEXES:")
    for tid, i in tt_data.teacher_index.items():
        print(f"   -- {tid:5} {i}")

    print("\n CLASS-GROUPS:")
    for klass, cgmap in tt_data.class_group_atoms.items():
        print("***** class", klass)
        for g, i in cgmap.items():
            print(f"   -- {g:5} {i}")
    print("  ... last index =", tt_data.n_class_group_atoms)

    print("\n ROOMS:")
    for r, i in tt_data.room_index.items():
        print(f"   -- {r:5} {i}")

# Not used here ...
    print("\n PARALLELS:")
    pmap = get_parallels()
    for tag in sorted(pmap):
        print(f"  // {tag:10} : {pmap[tag]}")

    print("\n TLESSONS  class 11G:")
    for tli in tt_data.class_ttls["11G"]:
        print("   --", tt_data.tt_lessons[tli])

    print("\n TLESSONS  teacher MT:")
    for tli in tt_data.teacher_ttls["MT"]:
        print("   --", tt_data.tt_lessons[tli])

    print("\n DIVISION GROUPS:")
    for k, divs in tt_data.group_division.items():
        print("  Class", k)
        print("    ::", divs)


    from pympler import asizeof
    print("\nSIZE:", asizeof.asizeof(tt_data.tt_lessons))
