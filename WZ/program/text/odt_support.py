"""
text/odt_support.py - last updated 2024-01-07

Support simple editing of odt-files (for LibreOffice) as templates.


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
    setup(os.path.join(basedir, 'TESTDATA'), debug = True)

#from core.base import Tr
#T = Tr("text.odt_support")

### +++++

import re

from core.base import REPORT_DEBUG
from tables.ods_support import (
    substitute_zip_content,
    XML_Reader,
    XML_writer,
)

### -----

ODT_TEXT = "text:p"
ODT_SPAN = "text:span"

def ODT_get_text(cell_node) -> str:
    text = ""
    for c in cell_node["children"]:
        #print("???", c)
        try:
            text += c["value"]
        except KeyError:
            if c["name"] in (ODT_TEXT, ODT_SPAN):
                for t in c["children"]:
                    try:
                        text += t["value"]
                    except KeyError:
                        REPORT_DEBUG(
                            "ODT_get_text\n"
                            f"Unhandled item in <{ODT_TEXT}>: {t}"
                        )
            else:
                REPORT_DEBUG(
                    "ODT_get_text\n"
                    f"Unhandled item in cell: {c}"
                )
    #if text: print("§ODT_get_text:", cell_node, "->", text)
    return text


def read_ODT_template(filepath: str) -> dict[str, int]:
    """Read the contents of the document seeking special text fields.
    These are delimited by [[ and ]].
    Return a mapping, delimiter-stripped key -> number of occurrences.
    """
    def fsub(m):
        k = m.group(1)
        print("$$$", k)
        try:
            keys[k] += 1
        except KeyError:
            keys[k] = 1
        return "?"

    def read_only(element: dict) -> bool:
        """A text-element handler for <ODT_Handler>, which just reads
        specially delimited text snippets.
        """
        if element["name"] in (ODT_SPAN, ODT_TEXT):
            text0 = ODT_get_text(element)
            text = regex.sub(fsub, text0)
            if text != text0:
                element["children"] = []
        return [element]

    def read_xml(xml: str) -> None:
        """A read-only handler for ods tables.
        """
        xml_handler = XML_Reader(
            process_element = read_only,
        )
        xml_handler.parse_string(xml)
        return None

    regex = re.compile(r"\[\[(.*?)\]\]")
    keys = {}
    substitute_zip_content(
        filepath,
        process = read_xml
    )
    return keys


#TODO
class ODT_Template:
    """Process a document element-by-element.
    Special text entries may be substituted from a supplied mapping.

    Information concerning the available fields can be returned.

    When performing a substitution, fields which are not substituted
    are returned as a list.
    """
    ## ODF keys



    TABLE = "table:table"
    TABLE_ROW = "table:table-row"
    TABLE_COL = "table:table-column"
    TABLE_CELL = "table:table-cell"
    COVERED_TABLE_CELL = "table:covered-table-cell"
    TABLE_STYLE = "table:style-name"
    REPEAT_ROW = "table:number-rows-repeated"
    REPEAT_COL = "table:number-columns-repeated"
    ROW_SPAN = "table:number-rows-spanned"
    COL_SPAN = "table:number-columns-spanned"
    VISIBLE = "table:visibility"
    HIDDEN = "collapse"
    VALUE_TYPE = "office:value-type"
    EXT_VALUE_TYPE = "calcext:value-type"
    STRING_TYPE = "string"
    TEXT = "text:p"
    PROTECT = {"table:protected": "true"}
    PROTECT_EXTRA = {
        "name": "loext:table-protection",
        "attributes": {
            "loext:select-protected-cells": "true",
            "loext:select-unprotected-cells": "true"
        },
        "children": []
    }

    def __init__(self,
        row_handler = None,     # function(row-element) -> bool
        table_handler = None,   # function(table-elements: list) -> dict
    ):
        """The table handler is called after the whole table has been
        read and is normally the function that is used for modifying the
        table.
        The row handler is called earlier and is convenient for reading
        the data on a row-by-row basis.
        It may also be used as a sort of pre-processor for rows.
        """
        self.row_handler = row_handler
        self.table_handler = table_handler

    def process_element(self, element) -> list[dict]:
        """This processes the given element and returns a list of
        elements to be added instead.
        """
        if element["name"] != self.TABLE:
            return [element]
        ## First pass, collect information about extents
        rows = []
        max_length = 0
        table_children = element["children"]
        for i, c in enumerate(table_children):
            if c["name"] == self.TABLE_ROW:
                ll = []
                for cc in c["children"]:
                    # Assume all children are cells or covered cells
                    ccn = cc["name"]
                    ccattrs = cc["attributes"]
                    if ccn == self.COVERED_TABLE_CELL:
                        # Count this as "used" even if empty
                        used = True
                    elif ccn == self.TABLE_CELL:
                        used = self.VALUE_TYPE in ccattrs
                    else:
                        REPORT_ERROR(
                            "Malformed ods-file?:\n"
                            f"Element '{ccn}' in table row"
                        )
                        used = True
                    try:
                        l = int(ccattrs[self.REPEAT_COL])
                    except:
                        l = 1
                    ll.append((used, l))
                # Count row length, not including empty trailing cells
                length = 0
                j = len(ll)
                while j > 0:
                    j -= 1
                    v, l = ll[j]
                    if v or length:
                        length += l
                if length > max_length:
                    max_length = length
                ll
                rows.append((length, i))
                #print("§row:", length, i)
        # Remove trailing empty rows
        while len(rows) > 1:
            length, i = rows[-1]
            if length:
                break
            del rows[-1]
            del table_children[i]
        #print(f"MAX LENGTH = {max_length}")

        ## Second pass, rebuild table
        new_table = []
        _col = 0
        for el in table_children:
            etype = el["name"]
            attrs = el["attributes"]

            if etype == self.TABLE_COL:
                if _col >= max_length:
                    # Lose this column descriptor
                    REPORT_DEBUG(f"Dropping column: {el}")
                    continue
                try:
                    rpt = int(attrs[self.REPEAT_COL])
                    del attrs[self.REPEAT_COL]
                except KeyError:
                    rpt = 1
                new_table.append(el)
                _col += 1
                while rpt > 1 and _col < max_length:
                    rpt -= 1
                    el = deepcopy(el)
                    new_table.append(el)
                    _col += 1

            elif etype == self.TABLE_ROW:
                # Rebuild the row, trimming excess columns and
                # expanding repeated cells.
                # Repeated rows are also expanded.
                try:
                    row_rpt = int(attrs[self.REPEAT_ROW])
                    del attrs[self.REPEAT_ROW]
                except KeyError:
                    row_rpt = 1
                cells = el["children"]
                new_row = []
                el["children"] = new_row
                subrows = [el]
                col = 0
                for cell in cells:
                    if col >= max_length:
                        # Lose this and any following cells
                        break
                    c_attrs = cell["attributes"]
                    try:
                        rpt = int(c_attrs[self.REPEAT_COL])
                        del c_attrs[self.REPEAT_COL]
                    except KeyError:
                        rpt = 1
                    new_row.append(cell)
                    col += 1
                    while rpt > 1 and col < max_length:
                        rpt -= 1
                        new_row.append(deepcopy(cell))
                        col += 1
                # Now handle repeated rows
                while row_rpt > 1:
                    row_rpt -= 1
                    subrows.append(deepcopy(el))
                # Pass the rows through the external handler, if any
                for el in subrows:
                    if self.row_handler:
                        if not self.row_handler(el):
                            continue
                    new_table.append(el)

            else:
                new_table.append(el)
        element["children"] = new_table
        if self.table_handler:
            info = self.table_handler(new_table)
            hidden_rows = info.get("hidden_rows") or []
            hidden_columns = info.get("hidden_columns") or []
            # Hide rows and columns
            col, row = 0, 0
            if hidden_columns or hidden_rows:
                for el in new_table:
                    etype = el["name"]
                    if etype == self.TABLE_COL and hidden_columns:
                        if col in hidden_columns:
                            el["attributes"][self.VISIBLE] = self.HIDDEN
                        col += 1
                    elif etype == self.TABLE_ROW and hidden_rows:
                        if row in hidden_rows:
                            el["attributes"][self.VISIBLE] = self.HIDDEN
                        row += 1
            # Add protection, if requested
            if info.get("protected"):
                element["attributes"].update(self.PROTECT)
                if new_table[0]["name"] != self.PROTECT_EXTRA["name"]:
                    new_table.insert(0, self.PROTECT_EXTRA)
        return [element]

    @classmethod
    def cell_text(cls, cell_node) -> str:
        text = ""
        for c in cell_node["children"]:
            if c["name"] == cls.TEXT:
                for t in c["children"]:
                    try:
                        text += t["value"]
                    except KeyError:
                        REPORT_DEBUG(
                            "ODS_Row_Handler\n"
                            f"Unhandled item in <{cls.TEXT}>: {t}"
                        )
            else:
                REPORT_DEBUG(
                    "ODS_Row_Handler\n"
                    f"Unhandled item in cell: {c}"
                )
        #print("§cell_text:", cell_node, "->", text)
        return text

    @classmethod
    def set_cell_text(cls, cell_node, text):
        """Set text in the given cell. If <text> is empty, the cell will
        be cleared.

        Existing children will be removed and a new text element added.
        Cell type will be set to "string".

        Handle only simple text items.
        """
        clist = cell_node["children"]
        clist.clear()
        atr = cell_node["attributes"]
        if text:
            tnode = {
                "name": cls.TEXT,
                "attributes": {},
                "children": [{"value": text}]
            }
            clist.append(tnode)
            atr[cls.VALUE_TYPE] = cls.STRING_TYPE
            atr[cls.EXT_VALUE_TYPE] = cls.STRING_TYPE
        else:
            try:
                del atr[cls.VALUE_TYPE]
                del atr[cls.EXT_VALUE_TYPE]
            except KeyError:
                pass


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import DATAPATH

    filepath = DATAPATH("testA.odt", "working_data")
    print("§KEYS in", filepath)
    keys = read_ODT_template(filepath)
    print("\n  ================================")
    print("\n -->", keys)

    quit(2)

    def read_xml(xml: str) -> str:
        handler = ODS_Handler(
            table_handler = extend,
        )
        xml_handler = XML_Reader(
            process_element = handler.process_element,
            report_clean = True
        )
        root = xml_handler.parse_string(xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)

    filepath = DATAPATH("testA.odt", "working_data")
    ods = substitute_zip_content(
        filepath,
        process = extend_xml
    )
    filepath = filepath.rsplit('.', 1)[0] + '_X.odt'
    with open(filepath, 'bw') as fh:
        fh.write(ods)
    print(" -->", filepath)

    def extend(elements):
        ODS_Handler.append_columns(elements, 3)
        ODS_Handler.add_rows(elements, 3, 1)
        rows = ODS_Handler.add_rows(elements, -1, 4)
        ODS_Handler.set_cell_text(rows[10]["children"][4], "nb")
        ODS_Handler.set_cell_text(rows[13]["children"][5], "3-")
        return {}

    def extend_xml(xml: str) -> str:
        handler = ODS_Handler(
            table_handler = extend,
        )
        xml_handler = XML_Reader(
            process_element = handler.process_element,
            report_clean = True
        )
        root = xml_handler.parse_string(xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)

    filepath = DATAPATH("testA.odt", "working_data")
    ods = substitute_zip_content(
        filepath,
        process = extend_xml
    )
    filepath = filepath.rsplit('.', 1)[0] + '_X.odt'
    with open(filepath, 'bw') as fh:
        fh.write(ods)
    print(" -->", filepath)

