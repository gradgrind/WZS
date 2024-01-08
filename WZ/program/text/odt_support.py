"""
text/odt_support.py - last updated 2024-01-08

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
        #print("$$$", k)
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


def write_ODT_template(
    filepath: str,
    fields: dict[str, str],
    special = None,
) -> tuple[bytes, dict[str, int], dict[str, str]]:
    """Read the contents of the document seeking special text fields.
    These are delimited by [[ and ]].
    Substitute these by the values supplied in <fields>.
    <special> is an optional function for replacing keys which are not
    in <fields>. It returns <None> if it receives a key it cannot handle.
    Return three items:
        - The modified file (bytes),
        - non-substituted fields in the document:
            mapping, field -> number of occurrences,
        - unused entries in <fields>:
            mapping, field -> value.
    """
    def fsub(m):
        k = m.group(1)
        #print("$$$", k)
        try:
            text = fields[k]
            used.add(k)
        except KeyError:
            try:
                text = special(k)
            except TypeError:
                text = None
            if text is None:
                try:
                    missing[k] += 1
                except KeyError:
                    missing[k] = 1
                text = "???"
        return text

    def replace(element: dict) -> bool:
        """A text-element handler for <ODT_Handler>, which substitutes
        specially delimited text snippets.
        """
        if element["name"] in (ODT_SPAN, ODT_TEXT):
            text0 = ODT_get_text(element)
            text = regex.sub(fsub, text0)
            if text != text0:
                element["children"] = [{"value": text}]
        return [element]

    def replace_xml(xml: str) -> None:
        """A snippet-replacement handler for odt documents.
        """
        xml_handler = XML_Reader(
            process_element = replace,
        )
        root = xml_handler.parse_string(xml)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + XML_writer(root)

    regex = re.compile(r"\[\[(.*?)\]\]")
    missing = {}
    used = set()
    odt = substitute_zip_content(
        filepath,
        process = replace_xml
    )
    unused = {
        k: v
        for k, v in fields.items()
        if k not in used
    }
    return odt, missing, unused


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import DATAPATH

    filepath = DATAPATH("testA.odt", "working_data")
    print("§KEYS in", filepath)
    keys = read_ODT_template(filepath)
    print("\n  ================================")
    print("\n -->", keys)

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

