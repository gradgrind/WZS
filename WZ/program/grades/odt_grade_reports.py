"""
grades/odt_grade_reports.py - last updated 2024-01-23

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
import local

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

#TODO: generate pdfs, move configs to CONFIG


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

#TODO: This should be in CONFIG somehow ...
FIELD_MAPPING = {
    "LEVEL": {"HS": "Hauptschule", "RS": "Realschule", "Gym": "Gymnasium"},
    "SEX": {"m": "Herr", "w": "Frau"},
    "OCCASION": {
        "2. Halbjahr": "1. und 2. Halbjahr",
        "$": "",
    }
}

#???
REPORT_FIELD_MAPPING = {
    "LEVEL": {
        "*/*": {"HS": "Hauptschule", "RS": "Realschule", "Gym": "Gymnasium"},
#        "occasion/class_group": {},
        # first look up occasion + class_group, then just occasion,
        # then just class_group, then default

        }

# ...
}

# OR put it all in a local module? together with the basic stuff below?


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
                try:
                    g = grade_map[g_pending][0]
                except KeyError:
                    g = "???"
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
        return []

    ## Get grades
    grade_table = GradeTable(occasion, class_group)
    grade_map = grade_table.grade_map

    students = db.table("STUDENTS")

    c, g = class_group_split(class_group)

    results = []
    for line in grade_table.lines:
        st_id = line.student_id
        fields = {
            "SCHOOL": CONFIG.SCHOOL,
            "OCCASION": occasion,
            "CLASS": c,
        }
        fields.update(students.all_string_fields(st_id))
        values = line.values
        subject_map = {}
        for i, dci in enumerate(grade_table.column_info):
            if dci.TYPE == "GRADE":
                print("???", dci)
                s = dci.DATA["SORTING"]
                val = (Subjects.clip_name(dci.LOCAL), values[i]) #???
                try:
                    subject_map[s].append(val)
                except KeyError:
                    subject_map[s] = [val]
            else:
                fields[dci.NAME] = values[i]
        print("§SUBJECT_MAP:", subject_map)
        for k, v in subject_map.items():
            v.reverse()
        print("§SUBJECT_MAP_REVERSED:", subject_map)

        fields.update(CALENDAR.all_string_fields())
        print("\n§FIELDS:", fields)

        # Make adjustments for specialities of the region or school-type
        local.reports.local_fields(fields)
        # Convert dates
        for f, val in fields.items():
            if f.startswith("DATE_"):
                if val:
                    try:
                        dateformat = CONFIG.GRADE_DATE_FORMAT
                    except KeyError:
                        dateformat = None
                    print("§dateformat:", dateformat, val)
                    val = print_date(val, dateformat)
                fields[f] = val
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

        results.append((odt, fields["SORTNAME"]))

        print("\n§MISSING:", m)
        print("\n§USED:", u)

    return results


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":

    _o = "1. Halbjahr"
    _cg = "12G.R"
    outdir = DATAPATH(f"{_o}/{_cg}".replace(" ", "_"), "working_data")
    print("§outdir", outdir)
    os.makedirs(outdir, exist_ok = True)
    for odt, sname in make_grade_reports(_o, _cg):
        outpath = os.path.join(outdir, sname) + ".odt"
        with open(outpath, 'bw') as fh:
            fh.write(odt)
        print(" -->", outpath)
