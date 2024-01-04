"""
tables/ods_support.py - last updated 2024-01-04

Support reading and simple editing of ods-tables (for LibreOffice).


=+LICENCE=============================
Copyright 2023 Michael Towers

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
#T = Tr("tables.ods_support")

### +++++

from typing import Optional
from copy import deepcopy

import zipfile as zf
import io
from xml.sax import parse, parseString
from xml.sax.handler import ContentHandler

from core.base import REPORT_WARNING

trtable = str.maketrans({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    "'": "&apos;",
    '"': "&quot;",
})
#+
def xmlesc(txt):
    """Use for text and attribute values if building xml "by hand".
    """
    return txt.translate(trtable)

### -----

####### XML parsing #######

class XML_Reader(ContentHandler):
    def __init__(self, process_element = None, report_clean = False):
        """Set up an XML reader.
        If a function is passed to <process_element>, each completed
        element will be processed by it. This function returns a list
        of elements which are to substitute the original element.

        If <report_clean> is true, empty elements will be
        reported. This is for testing purposes.
        """
        super().__init__()
        self.process_element = process_element
        self.report_clean = report_clean
        self._empty = []

    def parse_file(self, filepath: str) -> dict:
        self.element_stack = []
        parse(filepath, self)
        assert len(self.element_stack) == 1
        self.report_empty()
        return self.element_stack[0]

    def parse_string(self, xml: str) -> dict:
        self.element_stack = []
        parseString(xml, self)
        assert len(self.element_stack) == 1
        self.report_empty()
        return self.element_stack[0]

    def startElement(self, name: str, attrs):
        self.element_stack.append({
            "name": name,
            "attributes": dict(attrs),
            "children": [],
        })

    def endElement(self, name: str):
        if self.report_clean:
            element = self.element_stack[-1]
            try:
                if not element["value"]:
                    self._empty.append("NULL value")
            except KeyError:
                if not element["attributes"] and not element["children"]:
                    self._empty.append(f'NULL element: {element["name"]}')
        if len(self.element_stack) > 1:
            child = self.element_stack.pop()
            if self.process_element:
                children = self.process_element(child)
                if children:
                    self.element_stack[-1]["children"] += children
                return
            self.element_stack[-1]["children"].append(child)

    def characters(self, content: str):
        self.element_stack[-1]["children"].append({
            "value": content
        })

    def report_empty(self):
        if self._empty:
            elist = "\n".join(self._empty[:10])
            if len(self._empty) > 10:
                elist = f"{elist}\n ..."
            REPORT_WARNING(f"EMPTY ELEMENTS:\n {elist}")


def XML_writer(node: dict) -> str:
    """Write data in the form returned by XML_Reader to XML.
    """
    try:
        return xmlesc(node["value"])
    except KeyError:
        pass
    attrs = [
        f'{a}="{xmlesc(v)}"'
        for a, v in node["attributes"].items()
    ]
    children = [
       XML_writer(n)
       for n in node["children"]
    ]
    tag = node["name"]
    if attrs:
        tag1 = f'{tag} {" ".join(attrs)}'
    else:
        tag1 = tag
    if children:
        return f'<{tag1}>{"".join(children)}</{tag}>'
    else:
        return f'<{tag1}/>'

####### ODF file reader and modifier #######

_ODF_CONTENT_FILE = 'content.xml'
_ODF_META_FILE = 'meta.xml'
def substitute_zip_content(
    infile: str,
    process = None,
    metaprocess = None
) -> Optional[bytes]:
    """Process the contents of an ODF file using the function <process>.
    Return the resulting file as a <bytes> array.
    Normally the contents will be read; however, by setting <metaprocess>
    to a function, the metadata can be read.
    The processing function is given just the raw xml data and should
    return the modified xml.
    To read the data without modifying it, there should be only one
    processing function and this needs to save the data separately
    (<substitute_zip_content> has no provision for saving its data when
    not modifying the source) and return <None>. In this case
    <substitute_zip_content> will return <None>.
    """
    sio = io.BytesIO()
    with zf.ZipFile(sio, "w", compression=zf.ZIP_DEFLATED) as zio:
        with zf.ZipFile(infile, "r") as za:
            for fin in za.namelist():
                indata = za.read(fin)
                if fin == _ODF_CONTENT_FILE and process:
                    _indata = process(indata.decode(encoding = 'utf-8'))
                    if _indata:
                        indata = _indata.encode(encoding = 'utf-8')
                    else:
                        return None
                elif fin == _ODF_META_FILE and metaprocess:
                    _indata = metaprocess(indata.decode(encoding = 'utf-8'))
                    if _indata:
                        indata = _indata.encode(encoding = 'utf-8')
                    else:
                        return None
                zio.writestr(fin, indata)
    return sio.getvalue()

####### ODS handling #######

#TODO: It might not be too difficult to reinstate repeated rows and columns
# after any processing has been done? Is it worth it, though?

#TODO: sheet protection
'''
#Changed, at the start of the "table:table" node:
<table:table table:name="Sheet" table:style-name="ta1" table:protected="true">
#Added:
<loext:table-protection loext:select-protected-cells="true" loext:select-unprotected-cells="true"/>
# Was there previously:
<office:forms form:automatic-focus="false" form:apply-design-mode="false"/>
<table:table-column table:style-name="co1" table:default-cell-style-name="ce7"/>
'''


class ODS_Handler:
    """Process a table element by element.
    The table rows and columns are "expanded" to avoid difficulties with
    "repeated" elements in the XML. Also, trailing empty rows and columns
    are removed, but always leave one row, and each row should have at
    least one cell.

    Deletion and hiding of individual rows and columns is supported.
    """
    ## ODF keys
    TABLE = "table:table"
    TABLE_ROW = "table:table-row"
    TABLE_COL = "table:table-column"
    TABLE_CELL = "table:table-cell"
    COVERED_TABLE_CELL = "table:covered-table-cell"
    REPEAT_ROW = "table:number-rows-repeated"
    REPEAT_COL = "table:number-columns-repeated"
    VISIBLE = "table:visibility"
    HIDDEN = "collapse"
    VALUE_TYPE = "office:value-type"
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
        table_handler = None,   # function(table-elements: list)
        hidden_rows = None,     # iterable
        hidden_columns = None,  # iterable
        protected = False,
    ):
        self.row_handler = row_handler
        self.table_handler = table_handler
        if hidden_rows:
            self.hidden_rows = hidden_rows
        else:
            self.hidden_rows = []
        if hidden_columns:
            self.hidden_columns = hidden_columns
        else:
            self.hidden_columns = []
        self.protected = protected

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
                    cn = cc["name"]
                    assert cn in (self.TABLE_CELL, self.COVERED_TABLE_CELL)
                    ccattrs = cc["attributes"]
                    v = self.VALUE_TYPE in ccattrs
                    try:
                        l = int(ccattrs[self.REPEAT_COL])
                    except:
                        l = 1
                    ll.append((v, l))
                try:
                    r = int(c["attributes"][self.REPEAT_ROW])
                except KeyError:
                    r = 1

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
                rows.append((i, r, length, ll))

                print("  ???", i, r, length, ll)

        # Remove trailing empty rows
        while len(rows) > 1:
            i, r, length, ll = rows[-1]
            if length:
                break
            #print(f"DEL ROW {i} x {r}")
            del rows[-1]
            del table_children[i]
        #print(f"MAX LENGTH = {max_length}")

        ## Second pass, rebuild table
        new_table = []
        row = 0
        _col = 0
        for el in table_children:
            etype = el["name"]
            attrs = el["attributes"]

            if etype == self.TABLE_COL:
                if _col >= max_length:
                    # Lose this column descriptor
                    print(f"*** Debug, dropping column: {el}")
                    continue
                try:
                    rpt = int(attrs[self.REPEAT_COL])
                    del attrs[self.REPEAT_COL]
                except KeyError:
                    rpt = 1
                new_table.append(el)
                if _col in self.hidden_columns:
                    el["attributes"][self.VISIBLE] = self.HIDDEN
                _col += 1
                while rpt > 1 and _col < max_length:
                    rpt -= 1
                    el = deepcopy(el)
                    new_table.append(el)
                    if _col in self.hidden_columns:
                        el["attributes"][self.VISIBLE] = self.HIDDEN
                    _col += 1

            elif etype == self.TABLE_ROW:
                # Rebuild the row, trimming excess columns and
                # expanding repeated cells.
                # Repeated rows are also expanded.
                try:
                    row_rpt = int(attrs[self.REPEAT_ROW])
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
                    if row in self.hidden_rows:
                        el["attributes"][self.VISIBLE] = self.HIDDEN
                    row += 1
                    if self.row_handler:
                        if not self.row_handler(el):
                            continue
                    new_table.append(el)

            else:
                new_table.append(el)
        element["children"] = new_table
        if self.table_handler:
            self.table_handler(new_table)
        if self.protected:
            element["attributes"].update(self.PROTECT)
            new_table.insert(0, self.PROTECT_EXTRA)
        return [element]

    @staticmethod
    def cell_text(cell_node) -> str:
        text = ""
        for c in cell_node["children"]:
            if c["name"] == "text:p":
                for t in c["children"]:
                    try:
                        text += t["value"]
                    except KeyError:
                        REPORT_WARNING(
                            "Debug: ODS_Row_Handler\n"
                            f"Unhandled item in <text:p>: {t}"
                        )
            else:
                REPORT_WARNING(
                    "Debug: ODS_Row_Handler\n"
                    f"Unhandled item in cell: {c}"
                )
        #print("§cell_text:", cell_node, "->", text)
        return text

    @staticmethod
    def set_cell_text(cell_node, text):
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
                'name': 'text:p',
                'attributes': {},
                'children': [{'value': text}]
            }
            clist.append(tnode)
            atr["office:value-type"] = "string"
            atr["calcext:value-type"] = "string"
        else:
            try:
                del atr["office:value-type"]
                del atr["calcext:value-type"]
            except KeyError:
                pass

    @classmethod
    def delete_column(cls, elements: list[dict], col: int):
        """Remove the given column (0-indexed).
        If the value is negative, delete all columns starting at <- col>.
        """
        if col < 0:
            col0 = -col
        else:
            col0 = col
        c = 0
        for i, element in enumerate(elements):
            if element["name"] == cls.TABLE_COL:
                if c >= col0:
                    del elements[i]
                    if col >= 0:
                        break
                c += 1
        for element in elements:
            if element["name"] == cls.TABLE_ROW:
                cells = element["children"]
                if col < 0:
                    del cells[col0:]
                else:
                    del cells[col0]


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import DATAPATH

    def remove_column(elements):
        ODS_Handler.delete_column(elements, -22)

    def simple_xml(xml: str) -> str:
        handler = ODS_Handler(
            table_handler = remove_column,
            hidden_rows = [5],
            hidden_columns = [0],
            protected = True,
        )
        xml_handler = XML_Reader(
            process_element = handler.process_element,
            report_clean = True
        )
        root = xml_handler.parse_string(xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)

#TODO: Could add a file-chooser dialog for the source file
    filepath = DATAPATH("GRADES_SEK_I.ods", "TEMPLATES/GRADE_TABLES")
    #filepath = DATAPATH("test2.ods", "TEMPLATES/GRADE_TABLES")
    ods = substitute_zip_content(
        filepath,
        process = simple_xml
    )
    filepath = filepath.rsplit('.', 1)[0] + '_X.ods'
    with open(filepath, 'bw') as fh:
        fh.write(ods)
    print(" -->", filepath)
