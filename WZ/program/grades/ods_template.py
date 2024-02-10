"""
grades/ods_template.py - last updated 2024-02-10

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
from core.basic_data import CONFIG, CALENDAR
from core.dates import today
from tables.ods_support import (
    substitute_zip_content,
    XML_Reader,
    XML_writer,
    ODS_Handler,
    ODS_reader,
)
from grades.grade_tables import GradeTable

GRADE_TABLE_INFO = (
    ("+1", T("SCHOOL_YEAR")),
    ("+2", T("CLASS_GROUP")),
    ("+3", T("OCCASION")),
)

### -----


def readGradeTable(filepath: str):
    """Read the grade information, etc., from the given ods file.
    """
    info = {}
    grades = {}
    s_names = {}
    s_col = []
    for i, row in enumerate(ODS_reader(filepath)):
        #print(f"§§§ {i:03d}:", row)
        id = row[0]
        if not id:
            continue
        if id == '§0':
            # Read the subject keys, associate them with columns
            if s_col:
                REPORT_ERROR(T("REPEATED_LINE", tag = id, line = i + 1))
                continue
            for j in range(1, len(row)):
                stag = row[j]
                if stag:
#TODO: This version includes all "named" columns, the subjects are <str>
# values. Non-subject columns (like "LEVEL") would be included but might
# get the wrong local name – which might be in a different row.
#                    s_col.append((stag, j))
# This version uses <int> values for the subjects and doesn't include
# other columns (like "LEVEL").
                    try:
                        s_col.append((int(stag), j))
                    except ValueError:
                        pass
        elif id == '§+':
            # Subject line
            if s_names:
                REPORT_ERROR(T("REPEATED_LINE", tag = id, line = i + 1))
                continue
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


def inputGradeTable(filepath: str, grade_table: GradeTable
) -> list[tuple[int, dict[int, str]]]:
    """Read a table of grades (from a spreadsheet).
    Enter the grades into the given "GradeTable", checking the info-fields
    and subjects.
    Return a list of changes resulting from the insertions, including those
    resulting from the row calculations.
    """
    info, s_names, grades = readGradeTable(filepath)
    #print("\n§info:", info)
    #print("\n§SUBJECTS:", s_names)
    #for p_id, pgrades in grades.items():
    #    print("\n§PID:", p_id, pgrades)
    ## Check the info-fields
    try:
        key, trkey = GRADE_TABLE_INFO[0]
        if info[key][1] != CALENDAR.SCHOOL_YEAR:
            REPORT_ERROR(T("BAD_INFO",
                key = info[key][0],
                val = info[key][1],
                path = filepath,
            ))
            return
        key, trkey = GRADE_TABLE_INFO[1]
        if info[key][1] != grade_table.class_group:
            REPORT_ERROR(T("BAD_INFO",
                key = info[key][0],
                val = info[key][1],
                path = filepath,
            ))
            return
        key, trkey = GRADE_TABLE_INFO[2]
        if info[key][1] != grade_table.occasion:
            REPORT_ERROR(T("BAD_INFO",
                key = info[key][0],
                val = info[key][1],
                path = filepath,
            ))
            return
    except KeyError:
        REPORT_ERROR(T("MISSING_INFO", key = key, trkey = trkey))
        return
    ## Check that the input subjects match those in the "GradeTable"
    sset = set(s_names)
    keymap = []     # map subject-id to table column
    for c, dci in enumerate(grade_table.column_info):
        if dci.TYPE == "GRADE":
            s_id = int(dci.NAME)
            try:
                sset.remove(s_id)
            except KeyError:
                REPORT_WARNING(T("INPUT_SUBJECT_MISSING",
                    subject = dci.LOCAL
                ))
                continue
            keymap.append((s_id, c))
    if sset:
        REPORT_WARNING(T("INPUT_SUBJECTS_EXCESS",
            subjects = ', '.join(s_names[s_id] for s_id in sset)
        ))
    changes = []
    for r, line in enumerate(grade_table.lines):
        st_id = line.student_id
        gmap = grades[st_id]
        chdict = {}
        for s_id, c in keymap:
            val = gmap[s_id]
            chdict[c] = val
            grade_table.write_gt(r, c, val)
        chdict.update(grade_table.calculate_row(r))
        changes.append((r, chdict))
    return changes


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
        with_grades: bool = False
    ):
        self.row_count = 0
        self.hidden_rows = []
        self.hidden_columns = [0]
        self.subject_keys = {}
        self.subject_id_row = 0
        self.subject_name_row = 0
        self.start_col = 0
        self.start_row = 0

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

        self.grade_table = GradeTable(
            occasion = occasion,
            class_group = class_group,
            report_info = report_info,
            with_grades = with_grades,
        )
        self.info = {
            GRADE_TABLE_INFO[0][0]: CALENDAR.SCHOOL_YEAR, # e.g. "2024"
            GRADE_TABLE_INFO[1][0]: class_group,          # e.g. "12G.R"
            GRADE_TABLE_INFO[2][0]: occasion    # e.g. "2. Halbjahr", etc.
        }
        self.ods = substitute_zip_content(
            self.template_file,
            process = self.process_xml
        )

    def save(self, filepath):
        with open(filepath, 'bw') as fh:
            fh.write(self.ods)

    def process_row(self, element):
        cells = element["children"]
        c0 = ODS_Handler.cell_text(cells[0])
        if c0 == "§0":
            ## The line for subject keys, seek first subject column
            if self.subject_id_row:
                REPORT_ERROR(T("REPEATED_LINE",
                    tag = id, line = self.row_count + 1
                ))
                return False
            self.subject_id_row = self.row_count
            self.hidden_rows.append(self.row_count)
            i = 1
            for cell in cells[1:]:
                ci = ODS_Handler.cell_text(cell)
                if ci == "§1":
                    # First subject column
                    self.start_col = i
                    break
                elif ci:
                    self.subject_keys[ci] = i
                i += 1
        elif c0 == '§+':
            ## The line for the subject names
            if self.subject_name_row:
                REPORT_ERROR(T("REPEATED_LINE",
                    tag = id, line = self.row_count + 1
                ))
                return False
            self.subject_name_row = self.row_count
        elif c0 == "§":
            ## The first student line
            if self.start_row:
                REPORT_ERROR(T("REPEATED_LINE",
                    tag = id, line = self.row_count + 1
                ))
                return False
            self.start_row = self.row_count
        elif c0:
            ## Should be an info line
            try:
                text = self.info.pop(c0)
            except KeyError:
                text = None
                REPORT_WARNING(T("UNEXPECTED_INFO", key = c0))
            ODS_Handler.set_cell_text(cells[2], text)
        self.row_count += 1
        return True

    def process_table(self, elements):
        if not self.subject_id_row:
            REPORT_ERROR(T("NO_SUBJECT_ID_ROW"))
            return {}
        if not self.subject_name_row:
            REPORT_ERROR(T("NO_SUBJECT_NAME_ROW"))
            return {}
        if not self.start_col:
            REPORT_ERROR(T("NO_START_TAG"))
            return {}
        if not self.start_row:
            REPORT_ERROR(T("NO_STUDENT_ROW"))
            return {}
        if self.info:
            REPORT_ERROR(T("MISSING_INFO_FIELDS",
                fields = ", ".join(
                    f"{k} ({trk})"
                    for k, trk in GRADE_TABLE_INFO
                    if k in self.info
                )
            ))
        # Add rows for students, get row list
        student_list = self.grade_table.lines
        needed = len(student_list) - 1
        rows = ODS_Handler.add_rows(elements, self.start_row, needed)
        # Add columns for subjects
        cells = rows[self.subject_id_row]["children"] 
        subject_list = []
        val_col = []
        for i, dci in enumerate(self.grade_table.column_info):
            s_id = dci.NAME
            try:
                val_col.append(self.subject_keys[s_id])
            except KeyError:
                val_col.append(0)
            if dci.TYPE == "GRADE":
                subject_list.append((dci.NAME, dci.LOCAL, i))
        needed = self.start_col + len(subject_list) - len(cells)
        if needed > 0:
            ODS_Handler.append_columns(elements, needed)
        # Enter subject data
        cells1 = rows[self.subject_name_row]["children"]
        c = self.start_col
        for s_id, s_name, i in subject_list:
            val_col[i] = c
            self.subject_keys[s_id] = c
            ODS_Handler.set_cell_text(cells[c], s_id)
            ODS_Handler.set_cell_text(cells1[c], s_name)
            c += 1
        # Set the date
        cells = rows[0]["children"]
        i = len(cells)
        while i > 1:
            i -= 1
            if ODS_Handler.cell_text(cells[i]):
                ODS_Handler.set_cell_text(cells[i], today())
                break
        # Enter student data
        if student_list:
            i = self.start_row
            for stdata in student_list:
                cells = rows[i]["children"]
                ODS_Handler.set_cell_text(cells[0], str(stdata.student_id))
                ODS_Handler.set_cell_text(cells[1], stdata.student_name)
                for j, val in enumerate(stdata.values):
                    c = val_col[j]
                    if c and val:
                        ODS_Handler.set_cell_text(cells[c], val)
                i += 1
        return {
            "hidden_rows": self.hidden_rows,
            "hidden_columns": self.hidden_columns,
            "protected": True,
        }

    def process_xml(self, xml: str) -> str:
        handler = ODS_Handler(
            table_handler = self.process_table,
            row_handler = self.process_row,
        )
        xml_reader = XML_Reader(process_element = handler.process_element)
        root = xml_reader.parse_string(xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    db = get_database()

    filepath = DATAPATH("test_read_grades.ods", "working_data")
    print(f"*** READ GRADE TABLE {filepath}")
    info, s_names, grades = readGradeTable(filepath)
    print("\n§info:", info)
    print("\n§SUBJECTS:", s_names)
    for p_id, pgrades in grades.items():
        print("\n§PID:", p_id, pgrades)

    #quit(2)

    print("\n ***** Build Grade Input Tables *****")
    gt = BuildGradeTable("1. Halbjahr", "12G.R", with_grades = True)
    filepath = DATAPATH(gt.output_file_name, "working_data")
    gt.save(filepath)
    print(" -->", filepath)

    gt = BuildGradeTable("1. Halbjahr", "12G.G")
    filepath = DATAPATH(gt.output_file_name, "working_data")
    gt.save(filepath)
    print(" -->", filepath)

    gt = BuildGradeTable("1. Halbjahr", "11G")
    filepath = DATAPATH(gt.output_file_name, "working_data")
    gt.save(filepath)
    print(" -->", filepath)
