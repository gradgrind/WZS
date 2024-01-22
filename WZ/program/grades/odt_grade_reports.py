"""
grades/odt_grade_reports.py - last updated 2024-01-22

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
from core.subjects import Subjects
from text.odt_support import write_ODT_template
from grades.grade_tables import (
    GradeTable,


#    grade_table_data,
#    grade_scale,
#    valid_grade_map,
)

### -----

#TODO ...
_GRADE_REPORT_TEMPLATE = {
    "SEK_I": {
        "PATH": "GRADE_REPORTS/SekI",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "SEK_I_ABGANG": {
        "PATH": "GRADE_REPORTS/SekI-Abgang",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "SEK_I_ABSCHLUSS": {
        "PATH": "GRADE_REPORTS/SekI-Abschluss",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "SEK_I_ZWISCHEN": {
        "PATH": "GRADE_REPORTS/SekI-Zwischenzeugnis",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "SEK_II_ABGANG_12": {
        "PATH": "GRADE_REPORTS/SekII-12-Abgang",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "SEK_II_ABGANG_13": {
        "PATH": "GRADE_REPORTS/SekII-13-Abgang",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "SEK_II": {
        "PATH": "GRADE_REPORTS/SekII-12",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "SEK_II_13": {
        "PATH": "GRADE_REPORTS/SekII-13_1",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "Orientierung": {
        "PATH": "GRADE_REPORTS/Orientierung",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "Abitur": {
        "PATH": "GRADE_REPORTS/Abitur",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "Fachhochschulreife": {
        "PATH": "GRADE_REPORTS/Fachhochschulreife",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
    "Kein_Abitur": {
        "PATH": "GRADE_REPORTS/Abitur_nicht_bestanden",
        "FIELDS": [
            ["DATE_ISSUE", "Ausstellungsdatum"],
        ]
    },
}
print("§_GRADE_REPORT_TEMPLATE:", json.dumps(_GRADE_REPORT_TEMPLATE,
    ensure_ascii = False, separators = (',', ':')))

#####++++++++++++++++++++++++++++++++++++++++

_GRADE_REPORT_CHOICE = {
    "1. Halbjahr": {
        "12G.R": {
            "DATE_ISSUE": ["DATE_Halbjahr_1", "student>group"]
# Alternatives to "student>group": "student", "group"
        }
    },

}

# Actually, all reports have DATE_ISSUE, so it wouldn't need to be
# declared anywhere else. There is only the question of where the
# value comes from.

# I possibly also need the class's year part (for "Jahrgang" slots).

# In Sek II the students need to have an entry date for the
# "Qualifikationsphase". Although this is a group thing, it might be
# sensible to allow an override, just in case ... (it's one of those
# unclearly defined things in the "Verordnung").

#####++++++++++++++++++++++++++++++++++++++++


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
#TODO--
    gtemplates = _GRADE_REPORT_TEMPLATE
    tpath = gtemplates[tkey]["PATH"]
#TODO++
    #gtemplates = json.loads(CONFIG.GRADE_REPORT_TEMPLATE)
    #tpath = gtemplates[tkey]["PATH"]
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
    report_info: dict[str, list] = None, # <report_data()[0]>
    # The list items are:
    #   tuple[    db_TableRow,                # SUBJECTS record
    #             Optional[tuple[str, str]],  # title, signature
    #             list[db_TableRow]           # TEACHERS record
    #   ]
#?
    grades: dict = None
):
    def special(key):
        """Enter the subjects and grades in the template.
        """
#TODO: Handle subject keys ...
        nonlocal g_pending
        #print("§SPECIAL:", key)
        if key == "$":
            if g_pending is None:
                g = "!!!"
            elif g_pending == CONFIG.NO_GRADE_DOC:
                g = g_pending
            else:
                g = grade_map[g_pending][0]
            g_pending = None
            return g
        if key.startswith("."):
            for k in key[1:].split("."):
                try:
                    s, g_pending = subject_map[k].pop()
                    return s
                except KeyError:
                    continue
                except IndexError:
                    del subject_map[k]
            # No subjects left, add a null entry
            g_pending = CONFIG.NO_GRADE_DOC
            return CONFIG.NO_GRADE_DOC
        return None

    db = get_database()
    ## Get template
    template_file = get_template(occasion, class_group)
    if not template_file:
        return

#    gscale = grade_scale(class_group)
#    grade_map = valid_grade_map(gscale)

    ## Get grades
    grade_table = GradeTable(occasion, class_group)

    '''
    gtable = db.table("GRADES")
    info, subject_list, student_list = grade_table_data(
        occasion = occasion,
        class_group = class_group,
        report_info = report_info,
        grades = gtable.grades_for_occasion_group(occasion, class_group),
    )

    print("\nSUBJECTS:", subject_list)
    '''

    students = db.table("STUDENTS")

#TODO ... currently testing with just the first student
    n = 0

    line = grade_table.lines[n]
    st_id = line.student_id
    stdata = students.all_string_fields(st_id)
    values = line.values
    for i, dci in enumerate(grade_table.column_info):
        if dci.TYPE == "GRADE":
            print("???", dci)
        else:
            stdata[dci.NAME] = values[i]
    return


    print("\n$", student_list[n])
    st_n = student_list[n]
    st_id = st_n["id"]
    stdata = students.all_string_fields(st_id)
    gmap = st_n["GRADES"]
    print("§GRADES:", gmap)
    # Use LEVEL from grade table, as set up by <grade_table_data>
    stdata["LEVEL"] = gmap["LEVEL"]
    try:
        stdata["DATE_ISSUE"] = gmap["DATE_ISSUE"]
    except KeyError:
        # Get date-of-issue from CONFIG
        rdates = json.loads(CONFIG.REPORT_DATES)
        occ_dates = rdates.get(occasion)
        if occ_dates:
            d = occ_dates.get(class_group) or occ_dates.get("*")
            if d:
                if d.startswith("#"):
#TODO: catch look-up error
                    d = getattr(CALENDAR, d[1:])
                stdata["DATE_ISSUE"] = d
    subject_map = {}
    for sbj in subject_list:
        s = sbj.SORTING
        val = (Subjects.clip_name(sbj.NAME), gmap[str(sbj.id)])
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

#TODO
    stdata["REMARKS"] = (
        "A comment.\n"
        "A further comment.\n"
        "Something to sum the whole thing up without going into too much"
        " depth, but still saying something new.\n"
        "More? You must be kidding!"
    )

    c, g = class_group_split(class_group)
    fields = {
        "SCHOOL": CONFIG.SCHOOL,
        "SCHOOLBIG": CONFIG.SCHOOL.upper(),
        "OCCASION": occasion,
        "CLASS": c,
        "-REMARKS": "––––––––––––",
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
                    REPORT_ERROR(T("NO_FIELD_MAPPING",
                        field = f, value = val
                    ))
    print("\n$$$", fields)

    g_pending = None
    odt, m, u = write_ODT_template(template_file, fields, special)
    # If there are still entries in <subject_map> at the end of
    # the processing, these are unplaced values – report them.
    xs_subjects = []
    for sg in subject_map.values():
        xs_subjects += [ f"  -- {s}: {g}" for s, g in sg ]
    if xs_subjects:
        REPORT_ERROR(T("EXCESS_SUBJECTS", slist = "\n".join(xs_subjects)))

    print("\n§MISSING:", m)
    print("\n§USED:", u)

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
    print("\n§USED:", u)

    outpath = filepath.rsplit('.', 1)[0] + '_X.odt'
    with open(outpath, 'bw') as fh:
        fh.write(odt)
    print(" -->", outpath)

