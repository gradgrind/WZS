"""
grades/grade_tables.py - last updated 2024-01-08

Manage grade tables.


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
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import Tr
T = Tr("grades.grade_tables")

### +++++

from typing import Any
import json

from core.base import (
    DATAPATH,
#    REPORT_ERROR,
    REPORT_WARNING,
    REPORT_CRITICAL
)
from core.db_access import (
    DB_TABLES,
    db_Table,
    DB_PK,
    DB_FIELD_TEXT,
    DB_FIELD_JSON,
    DB_FIELD_REFERENCE,
)
from core.basic_data import CALENDAR, get_database, CONFIG
from core.classes import GROUP_ALL, class_group_split_with_id
from core.students import Students
from core.list_activities import report_data

NO_GRADE = '/'

### -----

class Grades(db_Table):
    table = "GRADES"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("OCCASION"),
                DB_FIELD_TEXT("CLASS_GROUP"),
                DB_FIELD_TEXT("TAG"),
                DB_FIELD_REFERENCE("Student", target = Students.table),
                DB_FIELD_TEXT("LEVEL"),
                DB_FIELD_JSON("GRADE_MAP"),
            )
            return True
        return False

    def grades_occasion_group(self,
        occasion: str,
        class_group: str,
        tag: str = "",
    ) -> dict[int, tuple[str, dict[int, str]]]:
        """Return a mapping with an entry for each student in the group
        who has an entry for the given occasion.
        The values are a pair:
            - LEVEL   (Use this level rather than that of the student,
                      which might have changed after this set of reports)
            - grade mapping: subject-id -> grade
        """
        # NOTE: The grades are stored as a list of pairs because
        # subject-ids are integers, which can't be keys in json.
        return {
            rec.Student.id: (rec.LEVEL, dict(rec.GRADE_MAP))
            for rec in self.records
            if (
                rec.OCCASION == occasion
                and rec.CLASS_GROUP == class_group
                and rec.TAG == tag
            )
        }
#+
DB_TABLES[Grades.table] = Grades


def subject_map(
    class_id: int,
    group: str = GROUP_ALL,
    report_info = None,
) -> tuple[dict, dict]:
    """<report_info> is class-info from <report_data()[0]>.
    Return subject information for the given class-group, as a mapping:
        {subject-id: {atomic-group-id: {set of teacher-ids}}}
    """
    db = get_database()
    classes = db.table("CLASSES")
    divdata = classes.group_data(class_id)
    group_info = divdata["group_info"]
    g_atoms = group_info[group].atomic_group_set
    #print("§g_atoms:", g_atoms)
    ## No-pupil- and no-teacher-groups are not filtered out by
    ## <report_data()>, but the course editor shouldn't let them be
    ## declared as having reports.
    smap = {}
    if not report_info:
        report_info = report_data(GRADES = True)[0]
    for s in report_info[class_id]:
        ## Filter subjects on group as well as class.
        #: s = (sbj, report_info, GROUP_TAG, tlist)
        s_id = s[0].id
        ags = group_info[s[2]].atomic_group_set
        #print("§s:", s[0].SID, s[2], ags, [t.Teacher.TID for t in s[3]])
        these_ags = ags & g_atoms
        if these_ags:
            tset = {t.Teacher.id for t in s[3]}
            try:
                sagmap = smap[s_id]
            except KeyError:
                sagmap = {}
                smap[s_id] = sagmap
            for ag in (these_ags):
                try:
                    sagmap[ag].update(tset)
                except KeyError:
                    sagmap[ag] = tset.copy()
    #print("\n§smap:", len(smap), smap)
    return smap


def students_grade_info(
    class_id: int,
    group: str,
    smap: dict[int, dict[int, set[int]]],
    #:: smap[s_id] = {atomic-group-id: {set of teacher-ids}}
):
    db = get_database()
    classes = db.table("CLASSES")
    subjects = db.table("SUBJECTS")
    divdata = classes.group_data(class_id)
    group_info = divdata["group_info"]
    if not group:
        REPORT_CRITICAL(
            "Bug: Null group passed to grade_tables::make_grade_table"
        )

    ## Build a sorted list of the subject objects
    slist = [subjects[s_id] for s_id in smap]
    slist.sort(key = lambda x: (x.SORTING, x.NAME))

    ## Build students list
    students = db.table("STUDENTS")
    allags = group_info[GROUP_ALL].atomic_group_set
    if group == GROUP_ALL:
        plist = students.student_list(class_id)
    else:
        plist = students.student_list(class_id, group)
    p_subjects = {}
    #:: {student_id: {{subject_id: { teacher_id, ... }}, ... } ... }
    for pdata in plist:
        #print("§pdata:", pdata)
        gfield = pdata.EXTRA.get("GROUPS") or ""
        ags = allags.copy()
        if gfield:
            for g in gfield.split():
                ags.intersection_update(group_info[g].atomic_group_set)
        #print("§ags:", ags)
        ## Collect sets of teachers for each subject.
        sbj2t = {}     # {s_id: { t_id, ... }}
        p_subjects[pdata.id] = sbj2t
        for sbj in slist:
            s_id = sbj.id
            agmap = smap[s_id]
            tset = set()
            for ag in ags:
                ts = agmap.get(ag)
                if ts:
                    tset.update(ts)
            #print("§tset:", s_id, tset)
            sbj2t[s_id] = tset
    return (slist, plist, p_subjects)


def grade_table_info(
    occasion: str,
    class_group: str,
    report_info = None,     # class-info from <report_data()[0]>
    grades = None
) -> tuple[
    dict[str, str],
    list[tuple[int, str, str]], # [(subject-id, sid, subject-name), ... ]
    list[dict[str, Any]]
]:
    """Collect the information necessary for grade input for the given group.
    If grades are supplied, include these.
    Return the general information fields, the subject list and the
    pupil list (with grade information).
    """
    class_id, group = class_group_split_with_id(class_group)
    if not group:
        REPORT_CRITICAL(
            "Bug: Null group passed to grade_tables::grade_table_info"
        )
    info = {
        "+1": CALENDAR.SCHOOL_YEAR, # e.g. "2024"
        "+2": class_group,          # e.g. "12G.R"
        "+3": occasion,             # e.g. "2. Halbjahr", "Abitur", etc.
    }
    #print("§info:", info)

    ## Get the subject data for this group
    smap = subject_map(class_id, group, report_info)
    ## ... and the student data
    subject_list, plist, p_subjects = students_grade_info(
        class_id, group, smap
    )

    ## Collect students
    student_list = []
    for pdata in plist:
        #print("§pdata:", pdata)
        pmap = {}
        student_list.append(pmap)
        pmap["§"] = pdata.id
        pname = pdata._table.get_name(pdata)
        pmap["§N"] = pname
        pmap["§M"] = pdata.EXTRA.get("LEVEL") or ""
        ## Write NO_GRADE where no teachers are available (based on group).
        ## Otherwise write grades, if supplied.
        if grades:
            try:
                pgrades = grades[pdata.id]
            except KeyError:
                pgrades = {}
        else:
            pgrades = {}
        sbjdata = p_subjects[pdata.id]
        #print("\n§1:", subject_list)
        #print("\n:§2:", sbjdata)
        glist = []
        pmap["GRADES"] = glist
        tlist = []
        pmap["TEACHERS"] = tlist
        for sbj in subject_list:
            gr = pgrades.get(sbj.id) or ""
            tset = sbjdata[sbj.id]
            tlist.append(tset)
            if tset:
                # There is a set of teachers
                glist.append(gr)
            else:
                # No teachers
                if gr and gr != NO_GRADE:
                    REPORT_WARNING(T("UNEXPECTED_GRADE",
                        grade = gr,
                        subject = sbj.NAME,
                        student = pname,
                    ))
                glist.append(NO_GRADE)
    #for s in student_list:
    #    print("\n %%%", s)
    return (info, subject_list, student_list)


def make_grade_table_ods(class_group, info, subject_list, student_list):
    ## Get template
    gscale = json.loads(CONFIG.GRADE_SCALE)
    grade_scale = (gscale.get(class_group) or gscale.get('*')
    )
    templates = json.loads(CONFIG.GRADE_TABLE_TEMPLATE)
    template_file = DATAPATH(templates[grade_scale], "TEMPLATES")
    print("§template:", template_file)
#TODO


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    db = get_database()

    ctable = db.table("CLASSES")
#TODO: Does report_data() need caching?
    c_reports, t_reports = report_data(GRADES = True)
    for c, items in c_reports.items():
        print("\n***", ctable[c].CLASS)
        for item in items:
            print("  --",
                item[0],
                item[1],
                item[2],
                ", ".join(t.Teacher.TID for t in item[3])
            )

    grades = {434: {6: "1+", 12: "4"}}
    cg = "12G.R"
#    cg = "13"
    occasion = "1. Halbjahr"

    info, subject_list, student_list = grade_table_info(
        occasion = occasion,
        class_group = cg,
        grades = grades,
    )

    make_grade_table_ods(cg, info, subject_list, student_list)
