"""
grades/grade_tables.py - last updated 2024-01-26

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

from typing import Any, Optional, NamedTuple
import json
from colorsys import rgb_to_hls, hls_to_rgb

from core.base import (
    REPORT_WARNING,
    REPORT_CRITICAL,
    REPORT_ERROR,
)
from core.db_access import (
    DB_TABLES,
    db_Table,
    db_TableRow,
    DB_PK,
    DB_FIELD_INTEGER,
    DB_FIELD_TEXT,
    DB_FIELD_JSON,
    DB_FIELD_REFERENCE,
    to_json,
)
from core.basic_data import CALENDAR, get_database, CONFIG, isodate
from core.classes import GROUP_ALL, class_group_split_with_id
from core.students import Students
from core.list_activities import report_data
import local

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
                DB_FIELD_REFERENCE("Student", target = Students.table),
                DB_FIELD_JSON("GRADE_MAP"),
            )
            return True
        return False

#TODO: deprecated
    def grades_occasion_group(self,
        occasion: str,
        class_group: str,
    ) -> dict[int, dict[int, str]]:
        """Return a mapping with an entry for each student in the group
        who has an entry for the given occasion.
        The values are mappings: str(subject-id) -> grade
        NOTE that the grade mapping can include also non-grade elements,
        like DATE_ISSUE and LEVEL (this LEVEL should be used rather than
        that of the student as the latter might have changed after this
        set of reports).
        """
        REPORT_WARNING(
            "<Grades.grades_occasion_group> is deprecated."
            " Use <Grades.grades_for_occasion_group> instead, noting"
            " the different returned structure."
        )
        return {
            rec.Student.id: rec.GRADE_MAP
            for rec in self.records
            if (
                rec.OCCASION == occasion
                and rec.CLASS_GROUP == class_group
#                and rec.TAG == tag
            )
        }

    class GradeMap:
        __slots__ = (
            "grades_id",    # int: GRADES.id
            "grades",       # dict[str, str]: GRADES.GRADE_MAP
        )
        def __init__(self, grades_id = None, grades = None):
            self.grades_id = grades_id
            self.grades = grades

    def grades_for_occasion_group(self,
        occasion: str,
        class_group: str,
    ) -> dict[int, GradeMap]:
        """Return a mapping with an entry for each student in the group
        who has an entry for the given occasion.
        The values are mappings: str(subject-id) -> <GradeMap> instance
        NOTE that the grade mapping can include also non-grade elements,
        like DATE_ISSUE and LEVEL (this LEVEL should be used rather than
        that of the student as the latter might have changed after this
        set of reports).
        """
        return {
            rec.Student.id: self.GradeMap(rec.id, rec.GRADE_MAP)
            for rec in self.records
            if (
                rec.OCCASION == occasion
                and rec.CLASS_GROUP == class_group
            )
        }
#+
DB_TABLES[Grades.table] = Grades


class GradeFields(db_Table):
    table = "GRADE_FIELDS"
    order = "SORTING"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_INTEGER("SORTING"),
                DB_FIELD_TEXT("NAME"),
                DB_FIELD_TEXT("LOCAL"),
                DB_FIELD_TEXT("TYPE"),
                DB_FIELD_JSON("DATA"),
                DB_FIELD_TEXT("COLOUR"),
                DB_FIELD_TEXT("FLAGS"),
                DB_FIELD_TEXT("GROUPS"),
            )
            return True
        return False
#+
DB_TABLES[GradeFields.table] = GradeFields


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


#TODO: Could this – or a slight variation of it – be used for text reports?
def students_grade_info(
    class_id: int,
    group: str,
    smap: dict[int, dict[int, set[int]]],
    #:: smap[s_id] = {atomic-group-id: {set of teacher-ids}}
):
    """Subject and student lists are returned for the given class and group.
    In addition, a mapping of subject-ids to the associated teacher-ids is
    provided for each student-id.
    The latter is provided using the mapping from the parameter <smap>, which
    is obtained by a call to <subject_map>.
    """
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
    #print("\n§slist:", slist)
    #print("\n§plist:", plist)
    #print("\n§p_subjects:", p_subjects)
    return (slist, plist, p_subjects)


def grade_table_data(
    occasion: str,
    class_group: str,
    report_info = None,     # class-info from <report_data()[0]>
    grades = None
) -> tuple[
    dict[str, str],
    list[db_TableRow], # list of "SUBJECTS" entries
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
        "+3": occasion              # e.g. "2. Halbjahr", "Abitur", etc.
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
        pmap["id"] = pdata.id
        pname = pdata._table.get_name(pdata)
        pmap["NAME"] = pname
        pmap["SORTNAME"] = pdata.SORTNAME
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
        gmap = {}
        pmap["GRADES"] = gmap
        tlist = []
        pmap["TEACHERS"] = tlist
        for sbj in subject_list:
            s_id = str(sbj.id)
            gr = pgrades.get(s_id) or ""
            tset = sbjdata[sbj.id]
            tlist.append(tset)
            if tset:
                # There is a set of teachers
                gmap[s_id] = gr
            else:
                # No teachers
                if gr and gr != NO_GRADE:
                    REPORT_WARNING(T("UNEXPECTED_GRADE",
                        grade = gr,
                        subject = sbj.NAME,
                        student = pname,
                    ))
                gmap[s_id] = NO_GRADE
        if "LEVEL" not in pgrades:
            gmap["LEVEL"] = pdata.EXTRA.get("LEVEL") or ""
        # Fetch non-grade items from <pgrades>
        for k, v in pgrades.items():
            try:
                # Test for subject key
                id = int(k)
                if k not in gmap:
                    REPORT_WARNING(T("UNEXPECTED_SUBJECT",
                        grade = gr,
                        subject = get_database().table["SUBJECTS"][id].NAME,
                        student = pname,
                    ))
            except ValueError:
                gmap[k] = v
    #for s in student_list:
    #    print("\n %%%", s)
    return (info, subject_list, student_list)


def grade_scale(class_group: str) -> str:
    gscale = json.loads(CONFIG.GRADE_SCALE)
    return gscale.get(class_group) or gscale.get('*')
#+
def valid_grade_map(gscale: str) -> dict[str, tuple[str, str]]:
    glist = json.loads(getattr(CONFIG, f"GRADE_TABLE_{gscale}"))
    grade_map = { g0: (g1, g2) for g0, g1, g2 in glist }
    #print("§grade_map:", grade_map)
    return grade_map






class DelegateColumnInfo:
    __slots__ = ("NAME", "LOCAL", "TYPE", "DATA", "FLAGS", "COLOUR")

    def __init__(self, rowdata: db_TableRow, **xargs):
        for s in self.__slots__:
            try:
                v = xargs.pop(s)
            except KeyError:
                v = getattr(rowdata, s)
            setattr(self, s, v)
        if xargs:
            REPORT_CRITICAL(
                "Bug, invalid parameter(s) passed to"
                " grades_manager::DelegateColumnInfo:\n"
                f"  {', '.join(xargs)}"
            )
        #print("§DelegateColumnInfo:", self)

    def __str__(self):
        l = [
            f"{s}={repr(getattr(self, s))}"
            for s in self.__slots__
        ]
        return f"DelegateColumnInfo({', '.join(l)})"

    def validate(self, value: str, write: bool = False
    ) -> Optional[str]:
        """Checks that the value is valid for this column.
        <write> should be true if writing the value – this allows blocking
        of writing to read-only columns.
        Return the LOCAL name if invalid, <None> if valid.
        """
        ctype = self.TYPE
        ok = True
        if ctype == "GRADE":
            if value not in self.DATA["valid"]:
                ok = False
        elif ctype == "CHOICE":
            if value not in self.DATA:
                ok = False
        elif ctype == "DATE":
            if isodate(value) is None:
                ok = False
        elif ctype[-1] == "!":
            ok = not write
        # Other column types are not checked
        #print("§validate:", self.LOCAL, ctype, value, "-->", ok)
        if ok:
            return None
        return self.LOCAL


def hex_colour_adjust(colour: str, factor: float):
    """Lighten or darken an rgb-colour in "#RRGGBB" form.
    """
    colhex = colour.lstrip('#')
    rgb = tuple(int(colhex[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    h, l, s = rgb_to_hls(*rgb)
    l = max(min(l * factor, 1.0), 0.0)
    rgb = hls_to_rgb(h, l, s)
    return "#" + "".join(f"{int(i * 255 + 0.5):02X}" for i in rgb)


#TODO: Use this INSTEAD of <grade_table_data>?
class GradeTable:
    class GradeTableLine(NamedTuple):
        student_id: int
        student_name: str
        grades: Grades.GradeMap
        values: list[str]
        teacher_sets: list[set[int]]

    def read(self, row: int, column: int) -> str:
#TODO: trap index error?
        return self.lines[row].values[column]

    def write(self, row: int, column: int, value: str):
#TODO: trap index error?
        self.lines[row].values[column] = value

    def __init__(self,
        occasion: str,
        class_group: str,
        report_info = None,    #type???
    ):
        # <report_info> is class-info obtained by calling <report_data()>
        # and taking the first of the pair of results.
#TODO: Do I really need the second result anywhere? It might be less
# confusing if it was scrapped ...
        # If <report_info> is not supplied, it will be fetched by the call
        # to <subject_map()>. Providing the possibility of passing it in as
        # a parameter means this data can be cached externally.
        db = get_database()
        class_id, group = class_group_split_with_id(class_group)
        if not group:
            REPORT_CRITICAL(
                "Bug: Null group passed to GradeTable"
            )

#TODO: Is this really the right place for this???
        self.info = {   # for external grade table
            "+1": CALENDAR.SCHOOL_YEAR, # e.g. "2024"
            "+2": class_group,          # e.g. "12G.R"
            "+3": occasion              # e.g. "2. Halbjahr", "Abitur", etc.
        }

        self.occasion = occasion
        self.class_group = class_group
        ## Get the subject data for this group
        smap = subject_map(class_id, group, report_info)
        ## ... and the student data
        subject_list, student_list, p_subjects = students_grade_info(
            class_id, group, smap
        )
        ## ... and any existing grade data
        grades = db.table("GRADES").grades_for_occasion_group(
            occasion, class_group
        )
#TODO: Possibility of NOT including grades?

        ## Set up grade arithmetic and validation
        gscale = grade_scale(class_group)
        self.grade_map = valid_grade_map(gscale)
        self.grade_arithmetic = local.grades.GradeArithmetic(self.grade_map)

        ### Collect the columns
        headers = []
        col_dci = []       # collect <DelegateColumnInfo> objects
        self.column_info = col_dci
        key_col = {}
        all_grade_cols = set() # collect columns with grades for "*"-subjects
        gfields = db.table("GRADE_FIELDS").records
        for gf_i, rec in enumerate(gfields):
            gl = rec.GROUPS
            if gl != '*' and class_group not in gl.split():
                continue
            # Convert "sid" lists to column lists. Note that only columns
            # that have already been added can be included!
            try:
                sids = rec.DATA["__SIDS__"]
            except (TypeError, KeyError):
                pass
            else:
                cols = []
                if sids == "*":
                    # All non-component grades, including composites
                    for i, dci in enumerate(col_dci):
                        if dci.TYPE == "GRADE":
                            if "C" not in dci.FLAGS:
                                cols.append(i)
                        elif dci.TYPE == "COMPOSITE!":
                            cols.append(i)
                else:
                    for sid in sids.split():
                        try:
                            cols.append(key_col[sid])
                        except KeyError:
                            pass
                rec.DATA["__COLUMNS__"] = cols
                #print("§__COLUMNS__:", rec.NAME, cols)
            ctype = rec.TYPE
            if ctype == "GRADE":
                ## Add the grade columns
                for sbj in subject_list:
                    i = len(headers)
                    key_col[sbj.SID] = i
                    headers.append(sbj.NAME)
                    col_dci.append(DelegateColumnInfo(rec,
                        NAME = str(sbj.id),
                        LOCAL = sbj.NAME,
                        DATA = {
                            "SID": sbj.SID,
                            "SORTING": sbj.SORTING,
                            "valid": self.grade_map,
                        }
                    ))
                    all_grade_cols.add(i)
                continue

            if ctype == "DATE":
                dci = DelegateColumnInfo(rec, DATA = {})
                if "C" in rec.FLAGS:
                    date0, kd = get_calendar_date(
                        rec.NAME, occasion, class_group
                    )
                    if date0:
                        dci.DATA["default"] = date0
                    else:
                        REPORT_WARNING(T("NO_DATE_IN_CALENDAR", key = kd))
                    dci.DATA["calendar_key"] = kd

            elif ctype == "COMPOSITE!":
                d_colour = hex_colour_adjust(rec.COLOUR, 0.9)
                components = []
                for col in rec.DATA["__COLUMNS__"]:
                    dci = col_dci[col]
                    if dci.TYPE != "GRADE":
                        REPORT_ERROR(T("COMPONENT_NOT_GRADE",
                            subject = rec.NAME,
                            sid = dci.NAME
                        ))
                        continue
                    if "C" in dci.FLAGS:
                        REPORT_ERROR(T("COMPONENT_NOT_UNIQUE",
                            sid = dci.DATA["SID"]
                        ))
                        continue
                    # Mark as component
                    dci.FLAGS += "C"
                    all_grade_cols.discard(col)
                    components.append(col)
                    dci.COLOUR = d_colour
                if not components:
                    REPORT_WARNING(T("COMPOSITE_WITHOUT_COMPONENTS",
                        subject = rec.NAME
                    ))
                    continue
                if rec.LOCAL:
                    all_grade_cols.add(len(headers))
                    rec.DATA["__COLUMNS__"] = components
                    dci = DelegateColumnInfo(rec)
                else:
                    continue

            elif rec.LOCAL:
                dci = DelegateColumnInfo(rec)

            else:
                continue

            key_col[rec.NAME] = len(headers)
            headers.append(rec.LOCAL)
            col_dci.append(dci)

        ### Add students
        lines = []
        self.lines = lines
        for i, stdata in enumerate(student_list):
            #print("%stadata:", stdata)
            pname = stdata._table.get_name(stdata)
            ## Write NO_GRADE where no teachers are available.
            ## Otherwise write grades, if supplied.
            try:
                pgrades = grades[stdata.id]
            except KeyError:
                pgrades = Grades.GradeMap(0, {})
            sbjdata = p_subjects[stdata.id]
            #print("\n§1:", subject_list)
            #print("\n:§2:", sbjdata)
            gmap = pgrades.grades
            values = []
            tlist = []
            for dci in col_dci:
                s_id = dci.NAME
                gr = gmap.get(s_id) or ""
                if (not gr):
                    if "S" in dci.FLAGS:
                        # Get value from student's data
                        try:
                            gr = stdata.EXTRA[s_id]
                        except KeyError:
                            try:
                                gr = getattr(stdata, s_id)
                            except AttributeError:
                                pass
                    elif "C" in dci.FLAGS:
                        try:
                            gr = dci.DATA["default"]
                        except KeyError:
                            pass
                try:
                    tset = sbjdata.get(int(s_id))
                except ValueError:
                    tset = None
                else:
                    if not tset:
                        # No teachers
                        if gr and gr != NO_GRADE:
                            REPORT_WARNING(T("UNEXPECTED_GRADE",
                                grade = gr,
                                subject = dci.LOCAL,
                                student = pname,
                            ))
                        gr = NO_GRADE
                tlist.append(tset)
                values.append(gr)
#TODO: Test for unexpected entries in gmap?
#REPORT_WARNING(T("UNEXPECTED_SUBJECT",
#    grade = gr,
#    subject = get_database().table["SUBJECTS"][id].NAME,
#    student = pname,
#))
            lines.append(self.GradeTableLine(
                student_id = stdata.id,
                student_name = pname,
                grades = pgrades,
                values = values,
                teacher_sets = tlist,
            ))
            #print("§GradeTableLine:", lines[-1])
            self.calculate_row(i)

    def calculate_row(self, row: int) -> dict[int, str]:
        #print("\n§calculate_row", row)
        line = self.lines[row]
        values = line.values
        calculated_cols = {}
        grades = line.grades.grades
        changed = False     # test for changes to <grades>
        for c, dci in enumerate(self.column_info):
            ctype = dci.TYPE
            if ctype[-1] == "!":
                # Calculate the value
                #print("???", dci)
                val = self.grade_arithmetic.calculate(
                    dci, values
                )
                if values[c] != val:
                    values[c] = val
                    calculated_cols[c] = val
            else:
                val = values[c]
                #print("???", val, "#", dci, "\n ++", grades)
            if "G" in dci.FLAGS:
                try:
                    if val == grades[dci.NAME]:
                        continue
                except KeyError:
                    if not val:
                        continue
                grades[dci.NAME] = val
                changed = True
        if changed:
            if line.grades.grades_id:
                get_database().table("GRADES").update_json_cell(
                    rowid = line.grades.grades_id,
                    field = "GRADE_MAP",
                    **grades,
                )
            else:
                new_id = get_database().table("GRADES").add_records([{
                    "OCCASION": self.occasion,
                    "CLASS_GROUP": self.class_group,
                    "Student": line.student_id,
                    "GRADE_MAP": to_json(grades),
                }])[0]
                line.grades.grades_id = new_id
        return calculated_cols

#TODO: --?
    def _validate(self, col: int, value: str, write: bool = False
    ) -> Optional[str]:
        """Checks that the value is valid for the given column.
        Return the LOCAL name if invalid, <None> if valid.
        """
        dci = self.column_info[col]
        ctype = dci.TYPE
        ok = True
        if ctype == "GRADE":
#            if value not in self.grade_map: # dci.DATA["valid"]?
            if value not in dci.DATA["valid"]:
                ok = False
        elif ctype == "CHOICE":
            if value not in dci.DATA:
                ok = False
        elif ctype == "DATE":
            if isodate(value) is None:
                ok = False
        elif ctype[-1] == "!":
            ok = not write
        # Other column types are not checked
        #print("§validate:", dci.LOCAL, ctype, value, "-->", ok)
        if ok:
            return None
        return dci.LOCAL


def get_calendar_date(name: str, occasion: str, group: str
) -> tuple[str, str]:
    cdates = CALENDAR.__REPORTS__
    # Strip off "DATE_"-prefix. This would also accept other prefixes.
    dname = name.split("_", 1)[1]
    key0 = f".{dname}/{occasion}/*"
    key = key0.replace("*", group)
    d = cdates.get(key)
    if d is None:
        return (cdates.get(key0) or "", key0)
    return (d, key)


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
