"""
grades/odt_grade_reports.py - last updated 2024-01-07

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
from core.basic_data import CONFIG
from core.dates import today
from text.odt_support import write_ODT_template
from grades.grade_tables import grade_table_info

### -----

#TODO ...


def get_template(occasion: str, class_group: str,) -> str:
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


def make_grade_reports(
    occasion: str,
    class_group: str,
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
    ## Get template
    template_file = get_template(occasion, class_group)
    if not template_file:
        return




    info, subject_list, student_list = grade_table_info(
        occasion = occasion,
        class_group = class_group,
        report_info = report_info,
        grades = grades,
    )



# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    db = get_database()


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

