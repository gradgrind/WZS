"""
tables/ods_template.py - last updated 2024-01-03

Use ods-tables (for LibreOffice) as templates.
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
    ODS_Row_Handler,
)

### -----


# Process table rows

row_count = 0
def process_row(element, rows):

    print("TODO")
    return True

    if len(rows) == 0:
        cells = element["children"]
        col = 0
        for i, c in enumerate(cells):
            print("  --", c)
            atr = c["attributes"]
            if ODS_Row_Handler.cell_text(c) == "$":
                print("§-index = ", i)
#??? Maybe rather cover the cell?
                ODS_Row_Handler.set_cell_text(c, None)
            try:
                repeat = int(atr["table:number-columns-repeated"])
            except KeyError:
                repeat = 1
            col += repeat
            print("%%%", repeat, col)

#        if row_count < 12:
#            print(f"\n§ROW {row_count:03d}:")
#            for c in element["children"]:
#                print("  --", c)


def process_xml(xml: str) -> str:

    row_handler = ODS_Row_Handler(row_handler = process_row)
    handler = XML_Reader(process_element = row_handler.process_row)
    root = handler.parse_string(xml)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import DATAPATH

#TODO: Could add a file-chooser dialog for the source file
    filepath = DATAPATH("GRADES_SEK_I.ods", "TEMPLATES/GRADE_TABLES")
    ods = substitute_zip_content(
        filepath,
        process = process_xml
    )
    filepath = filepath.rsplit('.', 1)[0] + '_X.ods'
    with open(filepath, 'bw') as fh:
        fh.write(ods)
    print(" -->", filepath)
