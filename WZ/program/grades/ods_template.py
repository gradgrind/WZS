"""
grades/ods_template.py - last updated 2024-01-06

Use ods-tables (ODF / LibreOffice) as templates for grade tables.


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
T = Tr("grades.ods_template")

### +++++

import json

from core.base import DATAPATH, REPORT_ERROR, REPORT_WARNING
from core.basic_data import CONFIG
from core.dates import today
from tables.ods_support import (
    substitute_zip_content,
    XML_Reader,
    XML_writer,
    ODS_Handler,
    ODS_reader,
)
from grades.grade_tables import grade_table_info

### -----


def readGradeTable(filepath: str):
    """Read the grade information from the given ods file.
    """
    info = {}
    grades = {}
    s_names = {}
    s_col = []
    for i, row in enumerate(ODS_reader(filepath)):
        #print(f"{i:03d}:", row)
        id = row[0]
        if not id:
            continue
        if id == '§':
            # Read the subject keys, associate them with columns
            if s_col:
                REPORT_ERROR(T("REPEATED_SID_LINE", line = i + 1))
                continue
            for j in range(1, len(row)):
                stag = row[j]
                if stag:
                    s_col.append((int(stag), j))
        elif id == '*':
            # Subject line
            for stag, j in s_col:
                s_names[stag] = row[j]
        elif s_col:
            # Student grades
            try:
                p_id = int(id)
            except ValueError:
                REPORT_ERROR(T("BAD_PID", line = i + 1, pid = id))
                continue
            pgrades = {}
            grades[p_id] = pgrades
            pgrades["__NAME__"] = row[1]
            for stag, j in s_col:
                pgrades[stag] = row[j]
        else:
            # Info tag
            info[id] = row[1:3]
    return (info, s_names, grades)


#TODO: Consider the possibility of adding rows and columns – it might
# simplify template construction.

class BuildGradeTable:
    def __init__(self,
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
        self.student_index = 0

        ## Get template
        gscale = json.loads(CONFIG.GRADE_SCALE)
        grade_scale = gscale.get(class_group) or gscale.get('*')
        templates = json.loads(CONFIG.GRADE_TABLE_TEMPLATE)
        self.template_file = DATAPATH(templates[grade_scale], "TEMPLATES")
        #print("§template:", self.template_file)
        if not self.template_file.endswith(".ods"):
            self.template_file = f"{self.template_file}.ods"

        # Suggestion for the output file name
        self.output_file_name = T("GRADE_FILE",
            occasion = occasion.replace(" ", "_"),
            group = class_group
        )

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

        self.ods = substitute_zip_content(
            self.template_file,
            process = self.process_xml
        )

    def save(self, filepath):
        with open(filepath, 'bw') as fh:
            fh.write(self.ods)

    def process_row(self, element):
        result = True    # retain row
        cells = element["children"]
        if self.row_count == 0:
            last = None
            for i, c in enumerate(cells):
                #print("  --", c)
                if c["children"]:
                    last = c
                    self.min_cols = i + 1
                elif c["name"] == ODS_Handler.COVERED_TABLE_CELL:
                    self.min_cols = i + 1
            ODS_Handler.set_cell_text(last, today())

        elif not self.subject_keys:
            ### Head/Info part
            c0 = ODS_Handler.cell_text(cells[0])
            if c0 == '§':
                self.hidden_rows.append(self.row_count)
                ## Add the subject keys
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
                            break
                        else:
                            self.subject_keys[ci] = (s_id, sname)
                            ODS_Handler.set_cell_text(cell, str(s_id))
                        i += 1
                    j += 1
                else:
                    if len(self.subject_list) > i:
                        REPORT_ERROR(T("TOO_FEW_COLUMNS",
                            n = len(self.subject_list) - i
                        ))
                while j < self.min_cols:
                    cell = cells[j]
                    ci = ODS_Handler.cell_text(cell)
                    self.subject_keys[ci] = (None, None)
                    ODS_Handler.set_cell_text(cell, None)
                    j += 1
                self.max_col = j
                #print("§max_col:", self.max_col)

            else:
                for i, c in enumerate(cells):
                    if (
                        c["children"]
                        or c["name"] == ODS_Handler.COVERED_TABLE_CELL
                    ):
                        if (i + 1) > self.min_cols:
                            self.min_cols = i + 1
                if c0:
                    try:
                        text = self.info[c0]
                    except KeyError:
                        text = None
                        REPORT_WARNING(T("MISSING_INFO", key = c0))
                    ODS_Handler.set_cell_text(cells[2], text)

        else:
            cell0 = cells[0]
            c0 = ODS_Handler.cell_text(cell0)
            if c0 == '§':
                # Add a student line
                try:
                    stdata = self.student_list[self.student_index]
                except IndexError:
                    # No students left, lose the row
                    return False
                #print("§stdata", stdata)
                self.student_index += 1
                ODS_Handler.set_cell_text(cell0, str(stdata['§']))
                grades = stdata["GRADES"]
                gi = 0
                for cell in cells[1:]:
                    ci = ODS_Handler.cell_text(cell)
                    if ci.startswith('§'):
                        try:
                            text = stdata[ci]
                        except KeyError:
                            try:
                                s_id, _ = self.subject_keys[ci]
                            except KeyError:
                                # No subjects left
                                break
                            else:
                                try:
                                    text = grades[gi]
                                except IndexError:
                                    text = None
                                gi += 1
                                ODS_Handler.set_cell_text(cell, text)
                        else:
                            ODS_Handler.set_cell_text(cell, text)

            elif c0 == '*':
                # Add the subject names
                for cell in cells[1:]:
                    ci = ODS_Handler.cell_text(cell)
                    if ci.startswith('§'):
                        try:
                            s_id, sname = self.subject_keys[ci]
                        except KeyError:
                            # No subjects left
                            break
                        else:
                            ODS_Handler.set_cell_text(cell, sname)
        self.row_count += 1
        return result

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
            "protected": True,
        }


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    db = get_database()

#TODO:
    filepath = DATAPATH("test_read_grades.ods", "working_data")
    print(f"*** READ GRADE TABLE {filepath}")
    info, s_names, grades = readGradeTable(filepath)
    print("\n§info:", info)
    print("\n§SUBJECTS:", s_names)
    for p_id, pgrades in grades.items():
        print("\n§PID:", p_id, pgrades)

    quit(2)

    gt = BuildGradeTable("1. Halbjahr", "12G.R",
#        grades = {434: {6: "1+", 12: "4"}}
    )
    filepath = os.path.join(
        os.path.dirname(gt.template_file),
        gt.output_file_name
    )
    gt.save(filepath)
    print(" -->", filepath)

    gt = BuildGradeTable("1. Halbjahr", "12G.G")
    filepath = os.path.join(
        os.path.dirname(gt.template_file),
        gt.output_file_name
    )
    gt.save(filepath)
    print(" -->", filepath)

    gt = BuildGradeTable("1. Halbjahr", "11G")
    filepath = os.path.join(
        os.path.dirname(gt.template_file),
        gt.output_file_name
    )
    gt.save(filepath)
    print(" -->", filepath)
