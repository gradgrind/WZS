"""
grades/odt_grade_reports.py - last updated 2024-01-08

Use odt-documents (ODF / LibreOffice) as templates for grade reports.


=+LICENCE=============================
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
=-LICENCE========================================
"""

if __name__ == "__main__":
    import os, sys

    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import Tr
T = Tr("grades.odt_grade_reports")

### +++++

import json

from core.base import DATAPATH, REPORT_ERROR, REPORT_WARNING
from core.basic_data import get_database, CONFIG, CALENDAR
from core.dates import today, print_date
from core.classes import class_group_split
from text.odt_support import write_ODT_template
from grades.grade_tables import grade_table_info

### -----

#TODO ...


def get_template(occasion: str, class_group: str) -> str:
    occ_group_key = json.loads(CONFIG.GRADE_REPORTS)
    try:
        occmap = occ_group_key[occasion]
    except KeyError:
        REPORT_ERROR(T("OCCASION_NO_TEMPLATES", occasion = occasion))
        return ""
    try:
        tkey = occmap[class_group]
    except KeyError:
        try:
            tkey = occmap["*"]
        except KeyError:
            REPORT_ERROR(T("GROUP_NO_TEMPLATES",
                occasion = occasion,
                group = class_group
            ))
            return ""
    gtemplates = json.loads(CONFIG.GRADE_REPORT_TEMPLATE)
    tpath = gtemplates[tkey]
    template_file = DATAPATH(tpath, "TEMPLATES")
    if not template_file.endswith(".odt"):
        template_file = f"{template_file}.odt"
        print("§template:", template_file)
    return template_file


#    # Suggestion for the output file name
#    output_file_name = T("GRADE_REPORT",
#        occasion = occasion.replace(" ", "_"),
#        group = class_group
#    )


FIELD_MAPPING = {
    "LEVEL": {"HS": "Hauptschule", "RS": "Realschule", "Gym": "Gymnasium"},
    "SEX": {"m": "Herr", "w": "Frau"},
    "OCCASION": {
        "2. Halbjahr": "1. und 2. Halbjahr",
        "$": "",
    }
}

def make_grade_reports(
    occasion: str,
    class_group: str,
    tag: str = "",
    report_info: dict[str, list] = None, # <report_data()[0]>
    # The list items are:
    #   tuple[    db_TableRow,                # SUBJECTS record
    #             Optional[tuple[str, str]],  # title, signature
    #             str,                        # group tag
    #             list[db_TableRow]           # TEACHERS record
    #   ]
#?
    grades: dict = None
):
    def special(key):
        """Enter the subjects and grades in the template.
        """
        nonlocal g_pending
        #print("§SPECIAL:", key)
        if key == "$":
            g = "!!!" if g_pending is None else g_pending
            g_pending = None
            return g
#TODO: I have a problem here detecting which keys are valid subject-keys
        for k in key:
            try:
                s, g_pending = subject_map[k].pop()
                return s
            except KeyError:
                return None
            except IndexError:
                pass
                #del subject_map[k]
        # No subjects left, add a null entry
        g_pending = "NULL_G"
        return "NULL_S"

#TODO: If there are still entries in subject_map at the end of
# the processing, these are unplaced values – report them.


    db = get_database()
    ## Get template
    template_file = get_template(occasion, class_group)
    if not template_file:
        return

    ## Get grades
    gtable = db.table("GRADES")
    gmap = gtable.grades_occasion_group(occasion, class_group, tag)
    info, subject_list, student_list = grade_table_info(
        occasion = occasion,
        class_group = class_group,
        report_info = report_info,
        grades = {
            k: v[1]
            for k, v in gmap.items()
        },
    )

    students = db.table("STUDENTS")
    subjects = db.table("SUBJECTS")

    print("\nSUBJECTS:", subject_list)


#TODO ... currently testing with just the first student
    n = 0
    print("\n$", student_list[n])
    st_n = student_list[n]
    st_id = st_n["§"]
    stdata = students.all_string_fields(st_id)
    # Use LEVEL from grade table, if there is an entry for this student
    try:
        stdata["LEVEL"] = gmap[st_id][0]
    except KeyError:
        pass
    grade_list = st_n["GRADES"]
    print("§GRADES:", grade_list)
    subject_map = {}
    for i, sbj in enumerate(subject_list):
        s = sbj.SORTING
        val = (subjects.clip_name(sbj.NAME), grade_list[i])
        try:
            subject_map[s].append(val)
        except KeyError:
            subject_map[s] = [val]
    print("§SUBJECT_MAP:", subject_map)
    for k, v in subject_map.items():
        v.reverse()
    print("§SUBJECT_MAP_REVERSED:", subject_map)

    stdata.update(CALENDAR.all_string_fields())
#TODO: add other fields

    c, g = class_group_split(class_group)

    fields = {
        "SCHOOL": CONFIG.SCHOOL,
        "SCHOOLBIG": CONFIG.SCHOOL.upper(),
        "OCCASION": occasion,
        "CLASS": c,
    }
    for f, val in stdata.items():
        if f.startswith("DATE_"):
            if val:
                try:
                    val = print_date(val, CONFIG.GRADE_DATE_FORMAT)
                except KeyError:
                    val = print_date(val)
            fields[f] = val
        else:
            try:
                fmap = FIELD_MAPPING[f]
            except KeyError:
                fields[f] = val
            else:
                try:
                    fields[f] = fmap[val]
                except:
                    if '$' in fmap :
                        fields[f] = val.replace('$', tag)
                    REPORT_ERROR(T("NO_FIELD_MAPPING",
                        field = f, value = val
                    ))
    print("\n$$$", fields)

    g_pending = None
    odt, m, u = write_ODT_template(template_file, fields, special)

    print("\n§MISSING:", m)
    print("\n§UNUSED:", u)

# Just for testing!
    outpath = template_file.rsplit('.', 1)[0] + '_X.odt'
    with open(outpath, 'bw') as fh:
        fh.write(odt)
    print(" -->", outpath)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":

    make_grade_reports("1. Halbjahr", "12G.R")

    quit(2)

    fields = {
        "SCHOOLBIG": "MY SCHOOL",
        "LEVEL": "My level",
        "SCHOOL": "My School",
        "SCHOOL_YEAR": "2024",
        "EXTRA": "Not included",
    }

    odt, m, u = write_ODT_template(filepath, fields)

    print("\n§MISSING:", m)
    print("\n§UNUSED:", u)

    outpath = filepath.rsplit('.', 1)[0] + '_X.odt'
    with open(outpath, 'bw') as fh:
        fh.write(odt)
    print(" -->", outpath)

