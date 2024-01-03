"""
tables/ods_support.py - last updated 2024-01-03

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
    """Use for text and attribute values if building xml "by hand"."""
    return txt.translate(trtable)

### -----

####### XML parsing #######

class XML_Reader(ContentHandler):
    def __init__(self, process_element = None, report_clean = False):
        """Set up an XML reader.
        If a function is passed to <process_element>, each completed
        element will be processed by it. This function must return a
        true value in order for the element to be retained.

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
                self.process_element(child)
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

class ODS_Row_Handler:
    """Process a table row by row.
    """
    def __init__(self, row_handler = None):
        self.row_handler = row_handler
        self.rows = []

    def process_row(self, element) -> bool:
        """An element has been parsed to <element>.
        If it is a table row, process it and add it to <self.rows>.
        Only if a true value is returned will the element be retained.
        """
        if element["name"] == "table:table-row":
            if self.row_handler:
                if not self.row_handler(element, self.rows):
                    return False
            self.rows.append(element)
        return True

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

    def dummy_xml(xml: str) -> str:
        handler = XML_Reader(report_clean = True)
        root = handler.parse_string(xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)

#TODO: Could add a file-chooser dialog for the source file
    filepath = DATAPATH("GRADES_SEK_I.ods", "TEMPLATES/GRADE_TABLES")
    ods = substitute_zip_content(
        filepath,
        process = dummy_xml
    )
    filepath = filepath.rsplit('.', 1)[0] + '_X.ods'
    with open(filepath, 'bw') as fh:
        fh.write(ods)
    print(" -->", filepath)
