# Deprecated, replaced by tt_basic_data.
# Some of the code might be of interest if I want bitmaps ...
"""
timetable/tt_base.py

Last updated:  2023-08-13

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

#T = TRANSLATIONS("timetable.tt_base")

### +++++

from typing import NamedTuple, Optional
#from dataclasses import dataclass

from core.basic_data import (
    get_classes,
    get_teachers,
    get_rooms,
    NO_CLASS,
    GROUP_ALL,
    NO_TEACHER
)
from core.db_access import db_select, db_query

class TT_DATA(NamedTuple):
    class_i: dict[str, int]
    class_group_bits: list[dict[str, int]]
    class_room: list[str]
    teacher_i: dict[str, int]
    teacher_bits: list[int]
    room_i: dict[str, int]

class COURSE_INFO(NamedTuple):
    klass: str
    group: str
    sid: str
    tid: str
    bsid: str
    room: str


#TODO: add "teachers" and "classgroups" fields.
# Remove "checkbits"
class TT_LESSON(NamedTuple):
    checkbits: int
    roomlists: tuple[list[int], list[list[int]], list[list[int]]]
    courselist: list[COURSE_INFO]
    lesson_id: int
    subject_tag: str
    length: int
    lesson_group: int
    time: str
    # These are only needed for initialisation
    placement0: str
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


def get_class_atoms():
    """Each atomic group within a class gets a unique index.
    The division groups need to be mapped to a list of these indexes.
    """
    c_g_map = {}    # { class: { group: [ index, ... ] } }
    # The NO_CLASS entry might be superfluous: there shouldn't be any
    # entries with a non-null group in the null class.
    c_g_map[NO_CLASS] = {GROUP_ALL: [0]}
    i = 0
    for klass, cdata in get_classes().items():
        #print("?", klass)
        if klass != NO_CLASS:
            gmap = {}
            c_g_map[klass] = gmap
            cg = cdata.divisions
            amap = {}
            for ag in cg.atomic_groups:
                i += 1
                amap[ag] = i
            for g, ags in cg.group_atoms().items():
                #print("???", g, ags)
                gmap[g] = [amap[ag] for ag in ags]
            if gmap:
                gmap[GROUP_ALL] = list(amap.values())
            else:
                i += 1
                gmap[GROUP_ALL] = [i]
            #print("  gmap:", gmap)
    return i, c_g_map


def get_room_map():
    """Each room gets a unique index, so that integers can be used
    instead of the tag (str) in speed critical code.
    The special room "+" (which indicates that a room is still needed
    and cannot be allocated directly in the timetable) is given index 0.
    The others follow contiguously.
    """
    rmap = {"+": 0}
    i = 0
    for r, n in get_rooms():
        i += 1
        rmap[r] = i
    return rmap


# Keep the bit stuff in case I want to use it sometime?
def get_teacher_bits(b):
    """Each teacher gets a unique index, so that integers can be used
    instead of the tag (str) in speed critical code. Index 0 is reserved
    for the null teacher (<NO_TEACHER>), the others follow contiguously.
    Also a vector of bit-tags is generated so that logical AND can be
    used to test timetable clashes.
    """
    timap = {NO_TEACHER: 0}
    tvec = [0]
    i = 0
    for tid in get_teachers().list_teachers():
        if tid != NO_TEACHER:
            i += 1
            timap[tid] = i
            tvec.append(b)
            b += b
    return timap, tvec, b


def get_class_bits(b):
    """Each class gets a unique index, so that integers can be used
    instead of the tag (str) in speed critical code. Index 0 is reserved
    for the null class (<NO_CLASS>), the others follow contiguously.
    Also bit-tags are generated for all usable class-groups, so that
    logical AND can be used to test timetable clashes. These are
    organised as a vector of mappings, one mapping per class, the keys
    being the groups, the values the bit-tags.
    """
    cmap = {}
    cimap = {NO_CLASS: 0}
    cgvec = [{GROUP_ALL: 0}]
    crvec = [""]
    i = 0
    for klass, cdata in get_classes().items():
        #print("?", klass)
        if klass != NO_CLASS:
            i += 1
            cimap[klass] = i
            gmap = {}
            cgvec.append(gmap)
            crvec.append(cdata.classroom)
            cg = cdata.divisions
            g0 = 0  # whole class / all atomic groups
            for ag in cg.atomic_groups:
                cmap[ag] = b
                g0 |= b
                b += b
            for g, ags in cg.group_atoms().items():
                #print("???", g, ags)
                bg0 = 0
                for ag in ags:
                    bg0 |= cmap[ag]
                gmap[g] = bg0
            if g0:
                gmap[GROUP_ALL] = g0
            else:
                gmap[GROUP_ALL] = b
                b += b
    return cimap, cgvec, crvec, b


def get_activity_groups(tt_data: TT_DATA):
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
    r_map = tt_data.room_i
    for rec in db_select(q):
        lg = rec["Lesson_group"]
        klass = rec["CLASS"]
        ci = tt_data.class_i[klass]
        rm = tt_data.class_room[ci]
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
        gbits = tt_data.class_group_bits[ci][group] if group else 0
        ti = tt_data.teacher_i[tid]
        tbits = tt_data.teacher_bits[ti]
        checkbits = gbits | tbits

        try:
            lg_data = lg_map[lg]
            lg_data[0] |= checkbits
            if room:
                lg_data[1].add(room)
            lg_data[2].append(row)

        except KeyError:
            lg_map[lg] = [
                checkbits,
                {room} if room else set(),
                [row],
            ]
    # Process the room choices
    for lg_data in lg_map.values():
        lg_data[1] = simplify_room_lists(
            [[r_map[r] for r in room_split(rx)] for rx in lg_data[1]]
        )
        #print("  -->", lg_data[1])
    return lg_map

# Each lg will have one or more classes (though the null class is
# possible, too) and one or more teachers (though the null teacher is
# possible, too).

def get_lg_lessons():
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


def collate_lessons(
    lg_ll: dict[int, list],
    lg_map: dict[int, list[int, set[str], list[tuple]]],
    rmap_i: dict[str, int],
):
#TODO: documentation
    tt_lessons = [None]   # (checkbits, list of room-choice lists, ???)

    class_activities = {}       # class -> list of tt_lesson indexes
    teacher_activities = {}     # teacher -> list of tt_lesson indexes
#TODO: ... or rather list of (lg, [tt_lesson indexes]) ?
#TODO: Use indexes for teachers(, subjects) and classes?
    for lg, ll in lg_ll.items():
        checkbits, roomlists, courselist = lg_map[lg]
        tids = set()
        classes = set()
        sid0, bsid0 = None, None
        for course in courselist:
            # Each row <courselist> must have the same bsid and, if bsid
            # is null, the same sid.
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

        for lid, l, t, p, rr in ll:
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

            if rr:
                rplist = [rmap_i[r] for r in rr.split(",")]
            else:
                rplist = []
            tt_lessons.append(TT_LESSON(
                checkbits,
                roomlists,
                courselist,
                lid,
                sid0,
                l,
                lg,
                t,
                p,
                rplist
            ))
    return tt_lessons, class_activities, teacher_activities


def room_split(room_choice: str) -> list[str]:
    """Split a room (choice) string into components.
    If there is a '+', it must be the last character, not preceded
    by a '/'.
    """
    rs = room_choice.rstrip('+')
    rl = rs.split('/') if rs else []
    if room_choice and room_choice[-1] == '+':
        rl.append('+')
    return rl


def simplify_room_lists(roomlists: list[list[int]]) -> Optional[
    tuple[
        list[int],          # required single rooms
        list[list[int]],    # fixed room choices
        list[list[int]]     # flexible room choices
    ]
]:
    """Simplify room lists, where possible, and check for room conflicts.

    The basic room specifications for the individual "tlessons" are
    processed into three separate lists (see result type).
    The number of entries in <roomlist> is taken to be the number of
    distinct rooms needed.
    This approach is in some respects not ideal, but given the
    difficulties of specifying concisely the room requirements for
    blocks containing multiple courses, it seemed a reasonable compromise.
    """
    ## Collect single room "choices" and remove redundant entries
    srooms = [] # (single) fixed room
    rooms = []  # "normal" room choice list
    xrooms = [] # "flexible" room choice list (with '+')
    for rchoice in roomlists:
        if rchoice[-1] == 0:    # '+'
            xrooms.append(rchoice[:-1])
        elif len(rchoice) == 1:
            r = rchoice[0]
            if r in srooms:
                return None     # Internal conflict!
            srooms.append(r)
        else:
            rooms.append(rchoice)
    i = 0
    while i < len(srooms):
        # Filter already-claimed rooms from the choice lists
        r = srooms[i]
        i += 1
        rooms_1 = []    # temporary buffer for rebuilding <rooms>
        for rlist in rooms:
            try:
                rlist.remove(r)
            except ValueError:
                rooms_1.append(rlist)
            else:
                if len(rlist) == 1:
                    rx = rlist[0]
                    if rx in srooms:
                        return None
                    # Add to list of single rooms
                    srooms.append(rx)
                else:
                    rooms_1.append(rlist)
        rooms = rooms_1
        # Filter already claimed rooms from the flexible choices
        for rlist in xrooms:
            try:
                rlist.remove(r)
            except ValueError:
                continue
    # Sort according to list length
    rl1 = [(len(rl), rl) for rl in rooms]
    rl2 = [(len(rl), rl) for rl in xrooms]
    rl1.sort()
    rl2.sort()
    return (
        srooms,
        [rl[1] for rl in rl1],
        [rl[1] for rl in rl2]
    )


def read_tt_db():
    """Read all timetable-relevant information from the database.
    """
    timap, tvec, b = get_teacher_bits(1)
    cimap, cgvec, crvec, b = get_class_bits(b)
    rimap = get_room_map()
    tt_data = TT_DATA(
        cimap,
        cgvec,
        crvec,
        timap,
        tvec,
        rimap,
    )
    lg_map = get_activity_groups(tt_data)
    lg_ll = get_lg_lessons()
    return tt_data, collate_lessons(lg_ll, lg_map, rimap)


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

    timap, tvec, b = get_teacher_bits(1)
    l = len(f"{b:b}")
    print("\n TEACHERS\n  bits bytes:", l-1, sys.getsizeof(b))
    for tid, i in timap.items():
        print(f"   -- {tid:5} {tvec[i]:0{l}b}")

    cimap, cgvec, crvec, b = get_class_bits(b)
    l = len(f"{b:b}")
    print("\n CLASS-GROUPS\n  bits bytes:", l-1, sys.getsizeof(b))
    for klass, i in cimap.items():
        gmap = cgvec[i]
        print("***** class", klass, crvec[i])
        for g, bits in gmap.items():
            print(f"   -- {g:5} {bits:0{l}b}")

    print("\n ROOMS:")
    rimap = get_room_map()
    for r, i in rimap.items():
        print(f"   -- {r:5} {i}")

    tt_data = TT_DATA(
        cimap,
        cgvec,
        crvec,
        timap,
        tvec,
        rimap,
    )

    #quit(0)

    lg_map = get_activity_groups(tt_data)

# Not used here ...
    print("\n PARALLELS:")
    pmap = get_parallels()
    for tag in sorted(pmap):
        print(f"  // {tag:10} : {pmap[tag]}")

    print("\n LG_LESSONS:")
    lg_ll = get_lg_lessons()
    for lg, ll in lg_ll.items():
        print("  **", lg)
        for l in ll:
            print("    --", l)

    print("\n TLESSONS:")
    tlessons, class_activities, teacher_activities = collate_lessons(
        lg_ll, lg_map, tt_data.room_i
    )
    for tl in tlessons:
        print("   --", tl)

    print("\n TLESSONS  class 11G:")
    for tli in class_activities["11G"]:
        print("   --", tlessons[tli])

    print("\n TLESSONS  teacher MT:")
    for tli in teacher_activities["MT"]:
        print("   --", tlessons[tli])

    print("\nc_g_map:")
    n_groups, c_g_map = get_class_atoms()
    for c, g_map in c_g_map.items():
        print("  Class:", c)
        for g, ilist in g_map.items():
            print("    --", g, ilist)
    print("  ... last index =", n_groups)

    from pympler import asizeof
    print("\nSIZE:", asizeof.asizeof(tlessons))
