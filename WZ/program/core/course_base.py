"""
core/course_base.py

Last updated:  2023-12-29

Support functions dealing with courses, lessons, etc.


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
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import TRANSLATIONS
T = TRANSLATIONS("core.course_base")

### +++++

from typing import NamedTuple, Optional, Self
import re

from core.base import (
    REPORT_CRITICAL,
    REPORT_ERROR,
    REPORT_WARNING,
)
from core.db_access import (
    DB_TABLES,
    db_Table,
    db_TableRow,
    DB_PK,
    DB_FIELD_TEXT,
#    DB_FIELD_JSON,
    DB_FIELD_REFERENCE,
    DB_FIELD_INTEGER,
    DB_FIELD_FIX,
)
from core.basic_data import (
    get_database,
    REPORT_SPLITTER,
    REPORT_ALL_NAMES,
    SUBJECT_SPLITTER,
    print_fix,
)
from core.classes import Classes, format_class_group
from core.teachers import Teachers
from core.subjects import Subjects
from core.rooms import Rooms, RoomGroups
from core.time_slots import TimeSlots

REPORT_WRITER = "Z" # flag for teacher's ROLE in table COURSE_TEACHERS
# Note that its presence does not indicate that there actually are
# reports for the course – that is set in the COURSE_BASE table.

## Regular expressions
# Block field: "<short name>:<full name>*<tag>#<notes>"
# "*<tag>" and "#<notes>" are optional
BLOCK_short = r"(\w+)"
BLOCK_subject = r"(\w[^*]*\w)"
BLOCK_tag = r"(\w+)"
BLOCK_PATTERN = (
    f"^{BLOCK_short}:{BLOCK_subject}(?:\*{BLOCK_tag})?(?:#(.*))?$"
)
WEIGHT_PATTERN = "^[1-9+-]$"  # for a constraint weight

### -----


class COURSE_LINE(NamedTuple):
    """An object of this class represents a single course line as returned
    by <filter_activities>. It is based on an entry in the COURSE_BASE
    table, but includes also the associated group and teacher lists.
    """
    course: db_TableRow
    group_list: list[db_TableRow]
    teacher_list: list[db_TableRow]

    fields = ("id", "Subject", "Groups", "Teachers")

    def show(self, field: str) -> str:
        if field == "id":
            return str(self.course.id)
        if field == "Subject":
            return self.course.Subject.NAME
        if field == "Groups":
            return ", ".join(
                format_class_group(g.Class.CLASS, g.GROUP_TAG)
                for g in self.group_list
            )
        if field == "Teachers":
            return ", ".join(
                f"{t.Teacher.TID}" for t in self.teacher_list
            )
        REPORT_CRITICAL(f"TODO: Unknown COURSE_LINE field: {repr(field)}")

    def info(self):
        g = ", ".join(
            format_class_group(g.Class.CLASS, g.GROUP_TAG)
            for g in self.group_list
        )
        t = ", ".join(f"{t.Teacher.TID}" for t in self.teacher_list)
        bl = self.course.Lesson_block.BLOCK
        b = f"({bl})" if bl else ""
        return (
            f"COURSE<{self.course.id}:{self.course.Subject.NAME}"
            f"{b} [{g} // {t}]>"
        )

    def get_classroom(self):
        if len(self.group_list) != 1:
            return 0
        return self.group_list[0].Class.Classroom.id

    def __str__(self):
        t = self.show
        return (
            f'<{t("id")}: {t("Subject")} | {t("Groups")} | {t("Teachers")}>'
        )


class BLOCK(NamedTuple):
    id: Optional[int] = None
    short: str = ""
    subject: str = ""
    tag: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def read(cls, value: str, id: int = None) -> Optional[Self]:
        if value:
            m = re.match(BLOCK_PATTERN, value)
            if not m:
                REPORT_ERROR(T["BAD_BLOCK_NAME"].format(block = value))
                return None
            return cls(id, *m.groups())
        else:
            return cls(id)

    def key(self):
        return f"{self.subject}*{self.tag}" if self.tag else self.subject

    def __str__(self):
        if self.subject:
            xtag = f"*{self.tag}" if self.tag else ""
            xnotes = f"#{self.notes}" if self.notes else ""
            return f"{self.short}:{self.subject}{xtag}{xnotes}"
        return ""


def course_line(course: db_TableRow) -> COURSE_LINE:
    """Construct a COURSE_LINE object from the given COURSE_BASE record.
    """
    db = get_database()
    cgtable = db.table("COURSE_GROUPS")
    cttable = db.table("COURSE_TEACHERS")
    ci = course.id
    groups = cgtable.get_course_groups(ci)
    teachers = cttable.get_course_teachers(ci)
    return COURSE_LINE(course, groups, teachers)


def blocks_info():
    """Collect information about the existing blocks.
    Block-names consist of the "subject" (name of the block) and an
    optional tag part starting with '*'. The latter is to help
    distinguish different blocks sharing a "subject". This combination
    uniquely defines a "block".
    There must also be a short prefix, separated by ':', which is used
    as an identifier where space is limited, such as in timetable slots.
    There may also be a suffix, after a '#', which serves as notes/comments.
    A minimal example, with key "Handwerk-Kunst":
        "HK:Handwerk-Kunst"
    A full example, with key "Hauptunterricht*OS":
        "HU:Hauptunterricht*OS#für die Oberstufe"
    """
    block_map = {}
    for lb in get_database().table("LESSON_BLOCKS").records:
        if lb.BLOCK:
            block = BLOCK.read(lb.BLOCK, lb.id)
            if block:
                key = block.key()
                if key in block_map:
                    REPORT_ERROR(T["BLOCK_KEY_REPEATED"].format(key = key))
                    continue
                block_map[key] = block
    return block_map


def block_courses(block_id: int) -> list[COURSE_LINE]:
    """Return a list of all courses attached to the specified LESSON_BLOCKS
    record.
    """
    return [
        course_line(course)
        for course in get_database().table("COURSE_BASE").records
        if course.Lesson_block.id == block_id
    ]


class LessonBlocks(db_Table):
    table = "LESSON_BLOCKS"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("BLOCK"),
                DB_FIELD_FIX("WORKLOAD"),
            )
            return True
        return False

DB_TABLES[LessonBlocks.table] = LessonBlocks


class ParallelTags(db_Table):
    table = "PARALLEL_TAGS"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("TAG"),
                DB_FIELD_TEXT(
                    "WEIGHT", pattern = WEIGHT_PATTERN, default = "+"),
            )
            return True
        return False

    @staticmethod
    def split_tag(parallel_tag: db_TableRow) -> tuple[str, str]:
        """Split a TAG field into category and tag.
        Return a tuple of these substrings.
        """
        if parallel_tag.id == 0:
            return ("", "")
        tag0 = parallel_tag.TAG
        try:
            t1, t2 = tag0.split('~', 1)
        except ValueError:
            t1 = ""
            t2 = tag0
        return (t1, t2)

    def tag_maps(self):
        """Return two tag mappings.
        The first maps the (unique) parallel tags to their corresponding
        records.
        For the second map the parallel tags are split on '~'. The first part
        is called the "category" and may be empty. It is mapped to the second
        part, which is called the "tag". In the case of an empty "category",
        the "tag" is the whole of the TAG field.
        """
        tm = self.__tag_map
        if not tm:
            for rec in self.records:
                tm[rec.TAG] = rec
                tag1, tag2 = self.split_tag(rec)
                try:
                    self.__category_map[tag1].append(tag2)
                except KeyError:
                    self.__category_map[tag1] = [tag2]
        return tm, self.__category_map

    def clear_caches(self):
        # Note that the caches must be cleared if the table is changed.
        self.__tag_map = {}
        self.__category_map = {}

DB_TABLES[ParallelTags.table] = ParallelTags


class LessonUnits(db_Table):
    table = "LESSON_UNITS"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_REFERENCE(
                    "Lesson_block",
                    target = LessonBlocks.table
                ),
                DB_FIELD_INTEGER("LENGTH"),
                DB_FIELD_REFERENCE("Time", target = TimeSlots.table),
                DB_FIELD_REFERENCE("Parallel", target = ParallelTags.table),
            )
            return True
        return False

    def get_block_units(self, block_id: int):
        """Return a list of lesson records for the given block (id).
        """
        try:
            return self.__bumap.get(block_id) or []
        except AttributeError:
            pass
        bumap = {}
        for rec in self.records:
            bi = rec.Lesson_block.id
            try:
                bumap[bi].append(rec)
            except KeyError:
                bumap[bi] = [rec]
        self.__bumap = bumap
        return bumap.get(block_id) or []

    def clear_caches(self):
        # Note that the caches must be cleared if the table is changed.
        self.__bumap = None

DB_TABLES[LessonUnits.table] = LessonUnits


class Courses(db_Table):
    table = "COURSE_BASE"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_REFERENCE("Subject", target = Subjects.table),
                DB_FIELD_REFERENCE(
                    "Lesson_block",
                    target = LessonBlocks.table
                ),
                DB_FIELD_FIX("BLOCK_COUNT", min = 0.0),
                DB_FIELD_REFERENCE(
                    "Room_group",
                    target = RoomGroups.table
                ),
                DB_FIELD_TEXT("REPORT"),
                DB_FIELD_TEXT("GRADES"),
                DB_FIELD_TEXT("INFO"),
            )
            return True
        return False

DB_TABLES[Courses.table] = Courses


class CourseRooms(db_Table):
    table = "TT_ROOMS"
    # Allows sorting within a course's list of rooms:
    order = "Course_id,SORTING"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_REFERENCE("Course", target = Courses.table),
                DB_FIELD_REFERENCE("Room", target = Rooms.table),
                DB_FIELD_INTEGER("SORTING")
            )
            return True
        return False

    def get_room_list(self, course_id: int) -> list[db_TableRow]:
        """Return the list of records referring to the specified course.
        Do not retain the result over changes to this table.
        """
        return [
            rec for rec in self.records
            if rec.Course.id == course_id
        ]

DB_TABLES[CourseRooms.table] = CourseRooms


class CourseGroups(db_Table):
    table = "COURSE_GROUPS"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_REFERENCE("Course", target = Courses.table),
                DB_FIELD_REFERENCE("Class", target = Classes.table),
                DB_FIELD_TEXT("GROUP_TAG"),
            )
            return True
        return False

    def get_class_courses(self, class_id: int) -> dict[int, db_TableRow]:
        """Return a mapping, {course-id: course-base record}, for the given
        class-id.
        """
        try:
            return self.__class_course_map.get(class_id) or {}
        except AttributeError:
            pass
        self.build_course_maps()
        return self.__class_course_map.get(class_id) or {}

    def get_course_groups(self, course_id: int) -> list[db_TableRow]:
        try:
            return self.__course_map.get(course_id) or []
        except AttributeError:
            pass
        self.build_course_maps()
        return self.__course_map.get(course_id) or []

    def clear_caches(self):
        # Note that the caches must be cleared if the table is changed.
        self.__class_course_map = None
        self.__course_map = None

    def build_course_maps(self):
        cmap = {}
        ccmap = {}
        for rec in self.records:
            c = rec.Course
            ci = c.id
            cci = rec.Class.id
            try:
                cimap = ccmap[cci]
            except KeyError:
                ccmap[cci] = {ci: c}
            else:
                cimap[ci] = c   # this may be an overwrite, but that's okay
            try:
                cglist = cmap[ci]
            except KeyError:
                cmap[ci] = [rec]
            else:
                # Warn if a course with multiple groups has a group with
                # no pupils (GROUP_TAG empty).
                if len(cglist) == 1:
                    cg = cglist[0]
                    if not cg.GROUP_TAG:
                        block = c.Lesson_block.BLOCK
                        REPORT_WARNING(T["COURSE_WITHOUT_PUPILS"].format(
                            klass = cg.Class.CLASS,
                            sbj = c.Subject.NAME,
                            block = f"({block})" if block else ""
                        ))
                if not rec.GROUP_TAG:
                    block = c.Lesson_block.BLOCK
                    REPORT_WARNING(T["COURSE_WITHOUT_PUPILS"].format(
                        klass = rec.Class.CLASS,
                        sbj = c.Subject.NAME,
                        block = f"({block})" if block else ""
                    ))
                cglist.append(rec)
                cglist.sort(key = lambda x: (x.Class.CLASS, x.GROUP_TAG))
        self.__class_course_map = ccmap
        self.__course_map = cmap

DB_TABLES[CourseGroups.table] = CourseGroups


class CourseTeachers(db_Table):
    table = "COURSE_TEACHERS"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_REFERENCE("Course", target = Courses.table),
                DB_FIELD_REFERENCE("Teacher", target = Teachers.table),
                DB_FIELD_FIX("PAY_FACTOR", min = 0.0),
                DB_FIELD_TEXT("ROLE")
            )
            return True
        return False

    def get_teacher_courses(self, teacher_id: int) -> dict[int, db_TableRow]:
        """Return a mapping, {course-id: course-base record}, for the given
        teacher-id.
        """
        try:
            return self.__teacher_course_map.get(teacher_id) or {}
        except AttributeError:
            pass
        self.build_course_maps()
        return self.__teacher_course_map.get(teacher_id) or {}

    def get_course_teachers(self, course_id: int) -> list[db_TableRow]:
        try:
            return self.__course_map.get(course_id) or []
        except AttributeError:
            pass
        self.build_course_maps()
        return self.__course_map.get(course_id) or []

    def clear_caches(self):
        # Note that the caches must be cleared if the table is changed.
        self.__teacher_course_map = None
        self.__course_map = None

    def build_course_maps(self):
        cmap = {}
        tcmap = {}
        for rec in self.records:
            c = rec.Course
            ci = c.id
            tci = rec.Teacher.id
            try:
                cimap = tcmap[tci]
            except KeyError:
                tcmap[tci] = {ci: c}
            else:
                cimap[ci] = c   # this may be an overwrite, but that's okay
            try:
                cmap[ci].append(rec)
            except KeyError:
                cmap[ci] = [rec]
        self.__teacher_course_map = tcmap
        self.__course_map = cmap

DB_TABLES[CourseTeachers.table] = CourseTeachers


def filter_activities(filter_field: str, value: int) -> list[COURSE_LINE]:
    """Collect the primary course data for the all courses satisfying
    the given filter constraint (CLASS, TEACHER or SUBJECT).

    The main components are subject, teacher(s), pupil-group(s), and
    possibly "block" for each course entry (in COURSE_BASE).
    Additional fields are also collected so as to enable access to
    room-wishes, payment info, etc.
    """
    db = get_database()
    # There is quite a bit of redundancy in the structures used here,
    # but as the raw(ish) table rows are used, which are retained anyway,
    # little extra space is consumed.
    #print("\n§COURSE_LINES:", repr(filter_field), repr(value))
    course_list = []
    cgtable = db.table("COURSE_GROUPS")
    cttable = db.table("COURSE_TEACHERS")
    if filter_field == "CLASS":
        if value == 0:
            # This is a special case where there are no entries in
            # COURSE_GROUPS. That means, all entries in COURSE_BASE with
            # no entries in COURSE_GROUPS
            for course in db.table("COURSE_BASE").records:
                ci = course.id
                if ci == 0: continue    # not a "real" COURSE_BASE entry
                if not cgtable.get_course_groups(ci):
                    groups = []
                    teachers = cttable.get_course_teachers(ci)
                    course_list.append(COURSE_LINE(course, groups, teachers))
                    #print("  --", course_list[-1])
        else:
            class_courses = cgtable.get_class_courses(value)
            #print("§class_courses:", class_courses)
            # Build course list
            for ci, course in class_courses.items():
                groups = cgtable.get_course_groups(ci)
                teachers = cttable.get_course_teachers(ci)
                course_list.append(COURSE_LINE(course, groups, teachers))
                #print("  --", course_list[-1])
    elif filter_field == "TEACHER":
        if value == 0:
            # This is a special case where there are no entries in
            # COURSE_TEACHERS. That means, all entries in COURSE_BASE with
            # no entries in COURSE_TEACHERS
            for course in db.table("COURSE_BASE").records:
                ci = course.id
                if ci == 0: continue    # not a "real" COURSE_BASE entry
                if not cttable.get_course_teachers(ci):
                    groups = cgtable.get_course_groups(ci)
                    teachers = []
                    course_list.append(COURSE_LINE(course, groups, teachers))
                    #print("  --", course_list[-1])
        else:
            teacher_courses = cttable.get_teacher_courses(value)
            #print("§teacher_courses:", teacher_courses)
            # Build course list
            for ci, course in teacher_courses.items():
                groups = cgtable.get_course_groups(ci)
                teachers = cttable.get_course_teachers(ci)
                course_list.append(COURSE_LINE(course, groups, teachers))
                #print("  --", course_list[-1])
    elif filter_field == "SUBJECT":
        # All courses must have a non-null subject.
        courses = db.table("COURSE_BASE")
        for course in courses.records:
            if course.Subject.id == value:
                ci = course.id
                groups = cgtable.get_course_groups(ci)
                teachers = cttable.get_course_teachers(ci)
                course_list.append(COURSE_LINE(course, groups, teachers))
                #print("  --", course_list[-1])
    else:
        REPORT_CRITICAL(
            f"Bug: In <filter_activities>, filter_field = '{filter_field}'"
        )
    # Sort on subject
    course_list.sort(key = lambda x: x.course.Subject.NAME)
    return course_list


def grade_report_field(course_data: COURSE_LINE, on: bool = None) -> bool:
    """If <on is None>, use the GRADES field of the COURSE_BASE record.
    Check the validity of the value.
    If the new value is different to the old one, update the database.
    Return the validated boolean value.
    """
    grades = course_data.course.GRADES
    if on is None:
        on = bool(grades)
    # A report is only possible if there is a real group and a teacher:
    if on:
        okg = False
        for cg in course_data.group_list:
            if cg.GROUP_TAG:
                okg = True
                break
        if not okg:
            REPORT_ERROR(T["GRADES_BUT_NO_PUPILS"].format(
                course = str(course_data)
            ))
            on = False
        elif not course_data.teacher_list:
            REPORT_ERROR(T["GRADES_BUT_NO_TEACHER"].format(
                course = str(course_data)
            ))
            on = False
    value = "X" if on else ""
    if value != grades:
        # Update database (and memory mirror)
        if not course_data.course._write("GRADES", value):
            REPORT_CRITICAL(
                f"Bug: The value '{value}' failed validation"
                " for the GRADES field in table COURSE_BASE"
            )
    return on


def text_report_field(course_data: COURSE_LINE, text: str = None
) -> tuple[bool, str, str]:
    """If <text is None>, use the REPORT field of the COURSE_BASE record.
    Check the validity of the value.
    If the new value is different to the old one, update the database.
    Return the split value (with-report, title, signature).
    """
    report = course_data.course.REPORT
    if text is None:
        text = report
    try:
        t1, t2 = text.split(REPORT_SPLITTER, 1)
        with_report = True
    except ValueError:
        with_report = bool(text)    # when non-empty assume "on"
        if with_report:
            REPORT_ERROR(T["BAD_REPORT_FIELD"].format(
                course = str(course_data)
            ))
        t1, t2 = "", ""
    # A report is only possible if there is a real group and a teacher:
    teacher_names = teachers_print_names(course_data.teacher_list, t2)
    if with_report:
        okg = False
        for cg in course_data.group_list:
            if cg.GROUP_TAG:
                okg = True
                break
        if not okg:
            REPORT_ERROR(T["REPORT_BUT_NO_PUPILS"].format(
                course = str(course_data)
            ))
            with_report, t1, t2 = False, "", ""
        elif not teacher_names:
            REPORT_ERROR(T["REPORT_BUT_NO_TEACHER"].format(
                course = str(course_data)
            ))
            with_report, t1, t2 = False, "", ""
    title = t1 or subject_print_name(course_data.course)
    sig = t2 if (t2 and t2 != REPORT_ALL_NAMES) else teacher_names
    value = f"{t1}{REPORT_SPLITTER}{t2}" if with_report else ""
    if value != report:
        # Update database (and memory mirror)
        if not course_data.course._write("REPORT", value):
            REPORT_CRITICAL(
                f"Bug: The value '{value}' failed validation"
                " for the REPORT field in table COURSE_BASE"
            )
    return (with_report, title, sig)


def subject_print_name(course: db_TableRow) -> str:
    return course.Subject.NAME.split(SUBJECT_SPLITTER)[0]


def report_teachers(teacher_list: list[db_TableRow]) -> list[str]:
    """Extract the teachers who have the report ROLE from the given
    list – only the SIGNE field is needed.
    """
    return [
        t.Teacher.SIGNED
        for t in teacher_list
        if REPORT_WRITER in t.ROLE
    ]


def teachers_print_names(teacher_list: list[db_TableRow], value: str) -> str:
    if value and value != REPORT_ALL_NAMES:
        return value    # override teacher list
    tlist = report_teachers(teacher_list)
    if tlist:
        if len(tlist) == 1:
            return tlist[0]
        if value:
            return ", ".join(tlist)
        return f'[{" / ".join(tlist)}]'
    return ""


def print_workload(
    workload: float,
    blocks: float,
    nlessons: int,
    teacher_list: list[tuple[str, float]]
) -> str:
    """Return a text representation of the workload (payment basis)
    for the given data.
    """
    if workload < 0.0:
        workload = abs(workload * nlessons)
    workload *= blocks
    tlist = [
        f"{tid}: {print_fix(workload * pf)}"
        for tid, pf in teacher_list
    ]
    return "; ".join(tlist)


def get_pay(teacher: int, course_data: COURSE_LINE, nlessons: int) -> float:
    workload = course_data.course.Lesson_block.WORKLOAD
    if workload < 0.0:
        workload = abs(workload * nlessons)
    workload *= course_data.course.BLOCK_COUNT
    for t in course_data.teacher_list:
        if t.Teacher.id == teacher:
            return workload * t.PAY_FACTOR
    REPORT_ERROR(
        f"Bug in course_base::get_pay. In course {course_data}:\n"
        f" teacher {t.Teacher} not found"
    )
    return 0.0


def workload_teacher(teacher_id: int, activity_list: list[COURSE_LINE]
) -> tuple[int, float]:
    """Calculate the total number of lessons and the pay-relevant
    workload.
    """
    db = get_database()
    ## Each lesson-unit in a lesson-block must be counted only once for
    ## the timetable slots, so keep track:
    lb_n = {}
    pay = 0.0
    nlessons = 0
    lesson_units = db.table("LESSON_UNITS")
    for course_data in activity_list:
        ## Get number of lessons
        lb = course_data.course.Lesson_block.id
        try:
            n = lb_n[lb]
        except KeyError:
            n = 0
            for l in lesson_units.get_block_units(lb):
                n += l.LENGTH
            # Only add to lesson count if lb not already used
            nlessons += n
            lb_n[lb] = n
        p = get_pay(teacher_id, course_data, n)
        pay += p
    return (nlessons, pay)


def workload_class(class_id: int, activity_list: list[COURSE_LINE]
) -> list[tuple[str, int]]:
    """Calculate the total number of lessons for the pupils.
    The results should cover all (sub-)groups.
    """
    db = get_database()
    classes = db.table("CLASSES")
    divdata = classes.group_data(class_id)
    #print("\n§divdata:", classes[class_id].CLASS, divdata)
    g2info = divdata["group_info"]
    ### Collect lessons per atomic group
    ## Each lesson-unit in a lesson-block must be counted only once FOR
    ## EACH GROUP, so keep track:
    lbsets = []
    ag2lessons = []
    for i, ag in enumerate(divdata["atomic_groups"]):
        ag2lessons.append(0)
        lbsets.append(set())
    lesson_units = db.table("LESSON_UNITS")
    ## Run through the courses/activities
    for course_data in activity_list:
        ## Run through each group connected with the course
        cg = None   # check that there is only one group for the class
        for g in course_data.group_list:
            if g.Class.id == class_id:
                if cg is None:
                    cg = g.GROUP_TAG
                else:
                    REPORT_ERROR(
                        f"Bug in course {course_data}:"
                        " multiple groups in one class"
                    )
        if not cg:
            continue    # no pupil groups involved
        ## Get number of lessons
        lb = course_data.course.Lesson_block.id
        n = 0
        for l in lesson_units.get_block_units(lb):
            n += l.LENGTH
        for ag in g2info[cg].atomic_group_set:
            lbset = lbsets[ag]
            if lb in lbset:
                continue    # lesson-block already counted
            lbset.add(lb)
            ag2lessons[ag] += n
    #print("§ag2lessons:", ag2lessons)
    ### Simplify groups: seek "actual" groups which cover the various
    ### numeric results
    #print("§ag2lessons:", ag2lessons)
    ln_lists = {}
    for ag, n in enumerate(ag2lessons):
        try:
            ln_lists[n].add(ag)
        except KeyError:
            ln_lists[n] = {ag}
    results = []
    agbitmap2g = divdata["agbitmap2g"]
    for n, agset in ln_lists.items():
        bitmap = 0
        for ag in agset:
            bitmap |= 2**ag
        g = agbitmap2g[bitmap]
        results.append((g, n))
    results.sort()
    #print("§results:", results)
    return results


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    db = get_database()

    filter_activities("CLASS", 1)

    print("\n?blocks_info:")
    bi = blocks_info()
    print("  ", bi)
