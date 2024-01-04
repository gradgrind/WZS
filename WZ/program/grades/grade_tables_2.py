"""
grades/grade_tables.py - last updated 2024-01-04

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

import json

from core.base import (
    DATAPATH,
    REPORT_ERROR,
    REPORT_WARNING,
    REPORT_CRITICAL
)
from core.db_access import db_TableRow
from core.basic_data import CALENDAR, get_database, CONFIG
from core.classes import GROUP_ALL, class_group_split_with_id
import core.students    # needed to initialize STUDENTS table
from core.list_activities import report_data

NO_GRADE = '/'

### -----

def subject_map(
    class_id: int,
    group: str = GROUP_ALL,
    report_info = None,         # class-info from <report_data()[0]>
) -> tuple[dict, dict]:
    """Return subject information for the given class-group.
    A pair of mappings is returned:
        - {subject-id: {atomic-group-id: {set of teacher-ids}}}
        - {subject-id: db_TableRow("SUBJECTS")}
    """
    db = get_database()
    classes = db.table("CLASSES")
    divdata = classes.group_data(class_id)
    group_info = divdata["group_info"]
    g_atoms = group_info[group].atomic_group_set
    #print("§g_atoms:", g_atoms)
    # No-pupil- and no-teacher-groups are not filtered out by <report_data()>,
    # but the course editor shouldn't let them be declared as having reports.
    smap = {}
    s_info = {}
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
            s_info[s_id] = s[0]
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
    #print("§smap:", smap)
    return (smap, s_info)


################################################################

def students_grade_info(
    class_id: int,
    group: str,
    smap: dict[int, dict[int, set[int]]],
    #:: smap[s_id] = {atomic-group-id: {set of teacher-ids}}
    s_info: dict[int, db_TableRow],
    #:: s_info = {subject-id: db_TableRow("SUBJECTS")}
):
    db = get_database()
    classes = db.table("CLASSES")
    divdata = classes.group_data(class_id)
    group_info = divdata["group_info"]
    if not group:
        REPORT_CRITICAL(
            "Bug: Null group passed to grade_tables::make_grade_table"
        )

    ## Build a sorted list of the subject objects
    slist = [s_info[s_id] for s_id in smap]
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
        gfield = pdata.EXTRA["GROUPS"]
        ags = allags.copy()
        if gfield:
            for g in gfield.split():
                ags.intersection_update(group_info[g].atomic_group_set)
        #print("§ags:", ags)
        ## Collect sets of teachers for each subject.
        subjects = {}     # {s_id: { t_id, ... }}
        p_subjects[pdata.id] = subjects
        for sbj in slist:
            s_id = sbj.id
            agmap = smap[s_id]
            tset = set()
            for ag in ags:
                ts = agmap.get(ag)
                if ts:
                    tset.update(ts)
            #print("§tset:", s_id, tset)
            subjects[s_id] = tset
    return (slist, plist, p_subjects)


################################################################


def make_grade_table(
    occasion: str,
    class_group: str,
    report_info = None,     # class-info from <report_data()[0]>
    grades = None
):# -> Optional[template]?:
    """Build a basic pupil/subject table for grade input using a
    template appropriate for the given group.
    If grades are supplied, fill the table with these.
    Return the template if successful, else <None>.
    """
#    db = get_database()
#    classes = db.table("CLASSES")
#    divdata = classes.group_data(class_id)
#    group_info = divdata["group_info"]

    ## Get template
    gscale = json.loads(CONFIG.GRADE_SCALE)
    grade_scale = (gscale.get(class_group) or gscale.get('*')
    )
    templates = json.loads(CONFIG.GRADE_TABLE_TEMPLATE)
    template_file = DATAPATH(templates[grade_scale], "TEMPLATES")
    print("§template:", template_file)
#    template = ClassMatrix(template_file)

    class_id, group = class_group_split_with_id(class_group)
    if not group:
        REPORT_CRITICAL(
            "Bug: Null group passed to grade_tables::make_grade_table"
        )

    info = {
        "+1": CALENDAR.SCHOOL_YEAR, # e.g. "2024"
        "+2": class_group,          # e.g. "12G.R"
        "+3": occasion,             # e.g. "2. Halbjahr", "Abitur", etc.
    }
    print("§info:", info)
#    template.setInfo(info)

#    for min_width, val in enumerate(template.rows[0]):
#        if val and min_width > 10:
#            break
#    else:
#        REPORT_WARNING(T("NO_MIN_COL", path = template.template))
#    print("$:", min_width)

#    return

#    ## Go through the template columns and check if they are needed:
#    rowix: list[int] = template.header_rowindex  # indexes of header rows
#    if len(rowix) != 2:
#        REPORT_ERROR(T("TEMPLATE_HEADER_WRONG", path = template.template))
#        return None
#    sidcol: list[tuple[str, int]] = []
#    sid: str

    ## Get the subject data for this group
    smap, s_info = subject_map(class_id, group, report_info)
    ## ... and the student data
    slist, plist, p_subjects = students_grade_info(
        class_id, group, smap, s_info
    )
    #for s in slist:
    #    print("  --", s)

    idlist = []
    sidlist = []
    sbjlist = []
    for sbj in slist:
        # Add subject
        sidlist.append(sbj.SID)
        idlist.append(sbj.id)
        sbjlist.append(sbj.NAME)
#TODO: DO I rather want the db id?
        print("§ ++", sbj.SID, sbj.NAME)

#        sid = sbj.SID
#        col: int = template.nextcol()
#        sidcol.append((sbj.id, col))
#        template.write(rowix[0], col, sid)
#        template.write(rowix[1], col, sbj.NAME)
    # Enforce minimum number of columns
#    while col < min_width:
#        col = template.nextcol()
#        template.write(rowix[0], col, "")
    # Delete excess columns
#    template.delEndCols(col + 1)

#    return

    ## Add students
#TODO
    studlist = []
    for pdata in plist:
        #print("§pdata:", pdata)
#        row = template.nextrow()
        pmap = {}
        studlist.append(pmap)
#TODO: id instead of PID?
        pmap["§"] = pdata.PID

#        template.write(row, 0, pdata.PID)
##        pname = students.get_name(pdata)
        pname = pdata._table.get_name(pdata)
#        template.write(row, 1, pname)
        pmap["§N"] = pname

#TODO: Is there a better way of discovering whether (and where) a "level"
# should be written?
#        if template.rows[row][3] == "X":
#            template.write(row, 3, pdata.EXTRA.get("LEVEL") or "")

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
        subjects = p_subjects[pdata.id]
        print("\n§1:", idlist)
        print("\n:§2:", subjects)

        glist = []
        pmap["GRADES"] = glist
        for s_id in idlist:
#        for s_id, col in sidcol:
#            gr = pgrades.get(s_id)
            gr = pgrades.get(s_id) or ""
            if subjects[s_id]:
                # There is a set of teachers
#                if gr:
#                    template.write(row, col, gr)
                glist.append(gr)
            else:
                # No teachers
                if gr and gr != NO_GRADE:
                    REPORT_WARNING(T("UNEXPECTED_GRADE",
                        grade = gr,
                        subject = s_info[s_id].NAME,
                        student = pname,
                    ))
#                template.write(row, col, NO_GRADE)#, protect = True)?
                glist.append(NO_GRADE)

    # Delete excess rows
#    row = template.nextrow()
#    template.delEndRows(row)
    # Protect non-writeable cells
#    template.protectSheet()
    # Hide "control" data
#    template.hideCol(0)
#    template.hideHeader0()
#    return template

    for s in studlist:
        print("\n %%%", s)

    return {}


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    #from core.base import DATAPATH

    '''
    configfile = DATAPATH("CONFINI.ini", "TEMPLATES")
    print("§§§§", configfile)

    import configparser
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'ServerAliveInterval': '45',
                     'Compression': 'yes',
                     'CompressionLevel': '9'}
    config['forge.example'] = {}
    config['forge.example']['User'] = 'hg'
    config['topsecret.server.example'] = {}
    topsecret = config['topsecret.server.example']
    topsecret['Port'] = '50022'     # mutates the parser
    topsecret['ForwardX11'] = 'no'  # same here
    config['DEFAULT']['ForwardX11'] = 'yes'
    config['DEFAULT']['MULTILINE'] = 'Line1\nLine2\n\ \ Indented'
    with open(configfile, 'w') as fh:
        config.write(fh)

    ...

    config.read(configfile)
    print(config["DEFAULT"]["MULTILINE"])
    '''

    from tables.matrix import ClassMatrix

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

#    quit(2)

#    filepath = DATAPATH("NOTEN_SEK_I", "TEMPLATES")
#    template = ClassMatrix(filepath)

    grades = {434: {6: "1+", 12: "4"}}

    template = make_grade_table(
        occasion = "1. Halbjahr",
        class_group = "12G.R",
        grades = grades,
    )
    if template:
        print(" ->", template.save(template.template + "__test1"))
