"""
grades/grade_tables.py - last updated 2024-02-12

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

from typing import Optional, NamedTuple
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
from core.list_activities import class_report_data
import local

NO_GRADE = '/'

### -----

#TODO: After editing this table, the grades manager would need reloading
# (resetting occasion and class-group) because the combo box selectors could
# have changed. Presumably, when loading a grade table, one should check the
# validity of the report-type values for each student.

class GradeTemplates(db_Table):
    table = "GRADE_REPORT_CONFIG"

    @classmethod
    def init(cls) -> bool:
        if cls.fields is None:
            cls.init_fields(
                DB_PK(),
                DB_FIELD_TEXT("OCCASION"),
                DB_FIELD_TEXT("CLASS_GROUP"),
                DB_FIELD_TEXT("REPORT_TYPE"),
                DB_FIELD_TEXT("TEMPLATE"),
            )
            return True
        return False

    def setup(self):
        tmap = {}
        self._template_info = tmap
        for rec in self.records:
            occ = rec.OCCASION
            cg = rec.CLASS_GROUP
            val = (rec.REPORT_TYPE, rec.TEMPLATE, rec.id)
            try:
                cgmap = tmap[occ]
            except KeyError:
                tmap[occ] = {cg: [val]}
            else:
                try:
                    tlist = cgmap[cg]
                except KeyError:
                    cgmap[cg] = [val]
                else:
                    tlist.append(val)
#+
DB_TABLES[GradeTemplates.table] = GradeTemplates


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
        The values are <GradeMap> instances.
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
    """<report_info> is class-info from <class_report_data()>.
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
    ## <class_report_data()>, but the course editor shouldn't let them be
    ## declared as having reports.
    smap = {}
    if not report_info:
        report_info = class_report_data(GRADES = True)
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
        gfield = pdata.GROUPS
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
            if value not in self.DATA["__ITEMS__"]:
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

    def write_gt(self, row: int, column: int, value: str):
        """Write to the table memory cell.
        Note that the GRADES database table is not updated. For that to
        happen, a later call to <calculate_row> is needed.
        """
#TODO: trap index error?
        line = self.lines[row]
        line.values[column] = value
        dci = self.column_info[column]
        if "S" in dci.FLAGS:
            # Update entry in STUDENTS
            students = get_database().table("STUDENTS")
            students.update_cell(line.student_id, dci.NAME, value)

    def update_all(self, col: int, val: str, val0: str = None
    ) -> list[tuple[int, dict[int, str]]]:
        #print("§update_all: TODO", col, val, val0)
        extra_changes = []
        for r, line in enumerate(self.lines):
            value0 = line.values[col]
            # Don't update if the existing (non-null) value differs
            # from the previous group value, or if the existing value
            # is the same as the new value.
            if value0 and (value0 != val0 or value0 == val):
                continue
            self.write_gt(r, col, val)
            # Update the database GRADES table, accumulate follow-on
            # changes (there probably aren't any, but just in case ...)
            extra_changes.append((r, self.calculate_row(r)))
        return extra_changes

    def __init__(self,
        occasion: str,
        class_group: str,
        report_info = None,    #type???
        with_grades: bool = True,
    ):
        # <report_info> is class-info obtained by calling
        # <class_report_data()>.
        # If <report_info> is not supplied, it will be fetched by the call
        # to <subject_map()>. Providing the possibility of passing it in as
        # a parameter means this data can be cached externally.
        db = get_database()
        class_id, group = class_group_split_with_id(class_group)
        if not group:
            REPORT_CRITICAL(
                "Bug: Null group passed to GradeTable"
            )
        self.occasion = occasion
        self.class_group = class_group
        self.tstag = f"GRADES:{self.occasion}#{self.class_group}"
        try:
            self.modified, _ = db.table("TIMESTAMPS")._timestamps[self.tstag]
        except KeyError:
            self.modified = ""
        ## Get the subject data for this group
        smap = subject_map(class_id, group, report_info)
        ## ... and the student data
        subject_list, student_list, p_subjects = students_grade_info(
            class_id, group, smap
        )
        ## ... and any existing grade data, if desired
        if with_grades:
            grades = db.table("GRADES").grades_for_occasion_group(
                occasion, class_group
            )
        else:
            grades = {}

        ## Set up grade arithmetic and validation
        self.grade_scale = grade_scale(class_group)
        self.grade_map = valid_grade_map(self.grade_scale)
        self.grade_arithmetic = local.grades.GradeArithmetic(self.grade_map)

        ### Collect the columns
        report_types = db.table("GRADE_REPORT_CONFIG")._template_info
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
                    if rec.LOCAL:
                        REPORT_WARNING(T("COMPOSITE_WITHOUT_COMPONENTS",
                            subject = rec.LOCAL
                        ))
                    continue
                if rec.LOCAL:
                    all_grade_cols.add(len(headers))
                    rec.DATA["__COLUMNS__"] = components
                    dci = DelegateColumnInfo(rec)
                else:
                    continue

            elif ctype == "CHOICE":
                try:
                    clist = rec.DATA["__CHOICE__"]
                except KeyError:
                    if rec.NAME == "REPORT_TYPE":
                        clist = ["-"] + sorted(
                            r[0]
                            for r in report_types[occasion][class_group]
                        )
                        #print("§REPORT TYPES:", clist)
                dci = DelegateColumnInfo(rec)
                dci.DATA["__ITEMS__"] = clist

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
            if with_grades:
                self.calculate_row(i)

    def calculate_row(self, row: int) -> dict[int, str]:
        """Calculate those fields in the current row which depend on others.
        Return a mappping {column -> value} of resulting changes.
        """
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
            # Set the change timestamp in the database.
            # The front end must know about it, too ...
            db = get_database()
            self.modified = db.table("TIMESTAMPS").set(self.tstag)
        return calculated_cols


def get_calendar_date(name: str, occasion: str, group: str
) -> tuple[str, str]:
    cdates = CALENDAR.__REPORTS__
    # Strip off "DATE_"-prefix. This would also accept other prefixes.
    dname = name.split("_", 1)[1]
    key0 = f".{dname}/{occasion}/*"
    key = key0.replace("*", group)
    try:
        d = cdates[key]
    except KeyError:
        # value specific to occasion + group not available
        try:
            d = cdates[key0]
        except KeyError:
            # default value for occasion not available
            return ("", key0)
    return (d, key)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    db = get_database()

    ctable = db.table("CLASSES")
#TODO: Does class_report_data() need caching?
    c_reports = class_report_data(GRADES = True)
    for c, items in c_reports.items():
        print("\n***", ctable[c].CLASS)
        for item in items:
            print("  --",
                item[0],
                item[1],
                item[2],
                ", ".join(t.Teacher.TID for t in item[3])
            )
