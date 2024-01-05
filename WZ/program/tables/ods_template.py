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

from tables.ods_support import (
    substitute_zip_content,
    XML_Reader,
    XML_writer,
    ODS_Handler,
)

### -----

#TODO: Strip excess rows and columns ...

# Process table rows

class ODS_GradeTable:
    def __init__(self):#, filepath: str):
        self.row_count = 0
        self.min_cols = 0
        self.hidden_rows = []
        self.hidden_columns = []

    def process_row(self, element):
        result = True    # retain row
        if self.row_count == 0:
            cells = element["children"]
            for i, c in enumerate(cells):
                print("  --", c)
                #atr = c["attributes"]
                if ODS_Handler.cell_text(c) == "$":
                    print("$-index = ", i)
                    self.min_cols = i + 1
#??? Maybe rather cover the cell?
                    ODS_Handler.set_cell_text(c, None)

#        if row_count < 12:
#            print(f"\n§ROW {row_count:03d}:")
#            for c in element["children"]:
#                print("  --", c)

        elif self.row_count > 20:
            result = False
        self.row_count += 1
        return result

    def process_xml(self, xml: str) -> str:
        handler = ODS_Handler(
            table_handler = self.process_table,
            row_handler = self.process_row,
            hidden_rows = self.hidden_rows,         # e.g. [5]
            hidden_columns = self.hidden_columns,   # presumably [0]
            protected = True,
        )
        xml_reader = XML_Reader(process_element = handler.process_element)
        root = xml_reader.parse_string(xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)

    def process_table(self, elements):
#TODO
        ODS_Handler.delete_column(elements, -22)



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
    from core.base import DATAPATH
    gt = ODS_GradeTable()
    gt.handle_file()
