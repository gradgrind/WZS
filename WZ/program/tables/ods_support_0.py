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

#TODO: Strip excess rows and columns ...
# Find last column with content, length of longest row ?

class ODS_Handler:
    """Process a table element by element.
    The basic version supports operations on rows and columns, note
    however that columns offer little scope for manipulation.
    Hiding individual rows and columns is supported.
#TODO ********************************************************
    Trailing empty rows and columns are removed.
    """
    ## ODF keys
    #REPEAT_ROW = "table:number-rows-repeated"
    REPEAT_COL = "table:number-columns-repeated"
    VISIBLE = "table:visibility"
    HIDDEN = "collapse"

    def __init__(self,
        row_handler = None,     # function(row-element) -> list[dict]
        column_handler = None,  # function(column-element) -> list[dict]
        hidden_rows = None,     # iterable
        hidden_columns = None,  # iterable
    ):
        self.row_handler = row_handler
        self.column_handler = column_handler
        if hidden_rows:
            self.hidden_rows = sorted(hidden_rows, reverse = True)
        else:
            self.hidden_rows = []
        if hidden_columns:
            self.hidden_columns = sorted(hidden_columns, reverse = True)
        else:
            self.hidden_columns = []
        self.rows = []
        self.col_elements = []
        self.col_count = 0

    def process_element(self, element) -> list[dict]:
        """This processes the given element and returns a list of
        elements to be added instead.
        """
        tag = element["name"]
        if tag == "table:table-row":
            return self.process_row(element)
        elif tag == "table:table-column":
            return self.process_column(element)
        elif tag == "table:table":
            for c in element["children"]:
                print("$$$", c["name"])
        return [element]

    def process_column(self, element) -> list[dict]:
        """This processes the given table-column element and returns a list
        of elements to be added instead.
        Handle hidden columns and perform further processing using
        <self.column_handler>, if present.
        Additionally, it adds the elements to <self.col_elements> and
        increments <self.col_count> appropriately.
        """
        attrs = element["attributes"]
        try:
            _n = attrs[self.REPEAT_COL]
            n = int(_n)
        except KeyError:
            n = 1
        new_col = self.col_count + n
        elements = [element]
        if self.hidden_columns:
            h = self.hidden_columns[-1]
            if h < new_col:
                # Hide a column covered by this element
                assert h >= self.col_count
                del self.hidden_columns[-1]
                if n != 1:
                    del attrs[self.REPEAT_COL]
                n0 = h - self.col_count
                n1 = new_col - h - 1
                if n0:
                    # Another element is needed
                    attrs_e = attrs.copy()
                    e = {
                        "name": "table:table-column",
                        "attributes": attrs_e,
                        "children": [],
                    }
                    elements.append(e)
                    if n0 > 1:
                        attrs[self.REPEAT_COL] = str(n0)
                    # Hide this new element
                    attrs_e[self.VISIBLE] = self.HIDDEN
                else:
                    # Hide the first column of this group
                    attrs[self.VISIBLE] = self.HIDDEN
                if n1:
                    # Another element is needed
                    attrs_e = attrs.copy()
                    e = {
                        "name": "table:table-column",
                        "attributes": attrs_e,
                        "children": [],
                    }
                    elements.append(e)
                    if n1 > 1:
                        attrs_e[self.REPEAT_COL] = str(n1)
        if self.column_handler:
            children = []
            for e in elements:
                children += self.column_handler(e)
            elements = children
        for e in elements:
            assert e["name"] == "table:table-column"
            self.col_elements.append(e)
            try:
                _n = e["attributes"][self.REPEAT_COL]
                n = int(_n)
            except KeyError:
                n = 1
            self.col_count += n
        return elements

    def process_row(self, element) -> list[dict]:
        """This processes the given table-row element and returns a list
        of elements to be added instead.
        Handle hidden rows and perform further processing using
        <self.row_handler>, if present.
        Additionally, the result is added to <self.rows>.
        """
        if len(self.rows) in self.hidden_rows:
            element["attributes"][self.VISIBLE] = self.HIDDEN
#TODO: Do I need to manage repeating rows, like columns? YES!
        if self.row_handler:
            children = self.row_handler(element, self.rows)
            if children:
                self.rows += children
            return children
        self.rows.append(element)
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


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import DATAPATH

    def simple_xml(xml: str) -> str:
        handler = ODS_Handler(hidden_rows = [5], hidden_columns = [0])
        xml_handler = XML_Reader(
            process_element = handler.process_element,
            report_clean = True
        )
        root = xml_handler.parse_string(xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)

#TODO: Could add a file-chooser dialog for the source file
    filepath = DATAPATH("GRADES_SEK_I.ods", "TEMPLATES/GRADE_TABLES")
    ods = substitute_zip_content(
        filepath,
        process = simple_xml
    )
    filepath = filepath.rsplit('.', 1)[0] + '_X.ods'
    with open(filepath, 'bw') as fh:
        fh.write(ods)
    print(" -->", filepath)
