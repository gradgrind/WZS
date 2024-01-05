"""
tables/ods_template.py - last updated 2024-01-05

Use ods-tables (ODF / LibreOffice) as templates.
Can be used to produce grade tables.


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

#from core.base import Tr
#T = Tr("tables.ods_template")

### +++++

import json

from core.base import DATAPATH, REPORT_ERROR
from core.basic_data import CONFIG
from tables.ods_support import (
    substitute_zip_content,
    XML_Reader,
    XML_writer,
    ODS_Handler,
)
from grades.grade_tables_2 import grade_table_info

### -----

#TODO: Strip excess rows and columns ...

# Process table rows

class ODS_GradeTable:
    def __init__(self):#, filepath: str):
        pass

    def make_grade_table(self,
        occasion: str,
        class_group: str,
        report_info: dict[str, list] = None, # <report_data()[0]>
        # The list items are:
        #   tuple[    db_TableRow,                # SUBJECTS record
        #             Optional[tuple[str, str]],  # title, signature
        #             str,                        # group tag
        #             list[db_TableRow]           # TEACHERS record
        #   ]
        grades: dict = None
    ):
        self.row_count = 0
        self.min_cols = 0
        self.hidden_rows = []
        self.hidden_columns = [0]
        self.subject_keys = {}
        self.max_col = 0

        ## Get template
        gscale = json.loads(CONFIG.GRADE_SCALE)
        grade_scale = gscale.get(class_group) or gscale.get('*')
        templates = json.loads(CONFIG.GRADE_TABLE_TEMPLATE)
        template_file = DATAPATH(templates[grade_scale], "TEMPLATES")
        #print("§template:", template_file)
        if not template_file.endswith(".ods"):
            template_file = f"{template_file}.ods"

        self.info, self.subject_list, self.student_list = grade_table_info(
            occasion = occasion,
            class_group = class_group,
            report_info = report_info,
            grades = grades,
        )

#Testing ...
#        self.subject_list += [
#            (101, "XA", "AAAAAAAAAAAAAAAAAAAA"),
#            (102, "XB", "BBBBBBBBBBBBBBBBBBBB"),
#            (103, "XC", "CCCCCCCCCCCCCCCCCCCC"),
#            (104, "XD", "DDDDDDDDDDDDDDDDDDDD"),
#            (105, "XE", "EEEEEEEEEEEEEEEEEEEE"),
#        ]


        ods = substitute_zip_content(
            template_file,
            process = self.process_xml
        )
        filepath = template_file.rsplit('.', 1)[0] + '_X.ods'
        with open(filepath, 'bw') as fh:
            fh.write(ods)
        print(" -->", filepath)

    def process_row(self, element):
        result = True    # retain row
        cells = element["children"]
        if self.row_count == 0:
            for i, c in enumerate(cells):
                #print("  --", c)
                #atr = c["attributes"]
                if ODS_Handler.cell_text(c) == "$":
                    print("$-index = ", i)
                    self.min_cols = i + 1
#??? Maybe rather cover the cell?
                    ODS_Handler.set_cell_text(c, None)

#--
        elif self.row_count > 20:
            result = False
#TODO: Be careful when deleting rows – consider what effect this has
# on <self.row_count>.

        else:
            c0 = ODS_Handler.cell_text(cells[0])
            if c0 == '§':
                if self.subject_keys:
                    # Add a student line
                    pass

                else:
                    # Add the subject keys
                    i = 0
                    j = 1
                    for cell in cells[1:]:
                        ci = ODS_Handler.cell_text(cell)
                        if ci.startswith('§'):
                            try:
                                s_id, sid, sname = self.subject_list[i]
                            except IndexError:
                                # No subjects left
                                self.max_col = j
                                print("§max_col:", self.max_col)
                                break
                            else:
                                key = sid
#TODO: Rather <key = str(s_id)>?
                                self.subject_keys[ci] = key
                                ODS_Handler.set_cell_text(cell, key)
                            i += 1
                        j += 1
                    else:
                        if len(self.subject_list) > i:
                            REPORT_ERROR("TODO: not enough columns")
                    while j < self.min_cols:
                        ODS_Handler.set_cell_text(cells[j], None)
                        j += 1
                    self.max_col = j



        self.row_count += 1
        return result

#TODO: Problem with hidden rows and columns! At present they cannot
# be determined based on the table contents. It should be fairly easy
# to adapt the row handling to allow a "hide" flag to be returned.
# But at present the hidden columns are done before the row handler
# is called.
    def process_xml(self, xml: str) -> str:
        handler = ODS_Handler(
            table_handler = self.process_table,
            row_handler = self.process_row,
        )
        xml_reader = XML_Reader(process_element = handler.process_element)
        root = xml_reader.parse_string(xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)

    def process_table(self, elements):
        if self.max_col:
            ODS_Handler.delete_column(elements, -self.max_col)
        return {
            "hidden_rows": self.hidden_rows,
            "hidden_columns": self.hidden_columns,
#            "protected": True,
        }



    def handle_file(self):
#TODO: Could add a file-chooser dialog for the source file
        filepath = DATAPATH("GRADES_SEK_I.ods", "TEMPLATES/GRADE_TABLES")
        #filepath = DATAPATH("GRADES_SEK_II.ods", "TEMPLATES/GRADE_TABLES")
        #filepath = DATAPATH("test2.ods", "TEMPLATES/GRADE_TABLES")
        ods = substitute_zip_content(
            filepath,
            process = self.process_xml
        )
        filepath = filepath.rsplit('.', 1)[0] + '_X.ods'
        with open(filepath, 'bw') as fh:
            fh.write(ods)
        print(" -->", filepath)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    db = get_database()
    gt = ODS_GradeTable()
    gt.make_grade_table("1. Halbjahr", "12G.R",
        grades = {434: {6: "1+", 12: "4"}}
    )
