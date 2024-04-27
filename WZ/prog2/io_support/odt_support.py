"""
text/odt_support.py - last updated 2024-04-27

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
    setup(basedir)

#from core.base import Tr
#T = Tr("io_support.odt_support")

### +++++

import re

from core.base import REPORT_DEBUG, REPORT_ERROR
from io_support.odf_support import (
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
        - used entries in <fields>:
            mapping, field -> number of replacements.
    """
    def fsub(m):
        k = m.group(1)
        #print("$$$", k)
        if k.startswith("-"):
            # A field which is shown only if the key without '-'
            # is empty
            if fields.get(k[1:]):
                return ""
        try:
            text = fields[k]
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
        else:
            try:
                used[k] += 1
            except KeyError:
                used[k] = 1
        return text

    def replace(element: dict) -> bool:
        """A text-element handler for <ODT_Handler>, which substitutes
        specially delimited text snippets.
        """
        if element["name"] in (ODT_SPAN, ODT_TEXT):
            text0 = ODT_get_text(element)
            text = regex.sub(fsub, text0)
            if text != text0:
                paras = text.splitlines()
                if len(paras) > 1:
                    if text0.startswith("[[") and text0.endswith("]]"):
                        # Only in this case are paragraphs possible
                        if element["name"] == ODT_TEXT:
                            # Return multiple paragraphs
                            attrs = element["attributes"]
                            return [
                                {   "name": ODT_TEXT,
                                    "attributes": attrs.copy(),
                                    "children": [{"value": line}]
                                }
                                for line in paras
                            ]
                    REPORT_ERROR(T("INVALID_MULTILINE",
                        key = text0, val = "¶\n".join(paras)
                    ))
                else:
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
    used = {}
    odt = substitute_zip_content(
        filepath,
        process = replace_xml
    )
    return odt, missing, used


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import DATAPATH

    filepath = DATAPATH("Mantel.odt", "TEMPLATES/TEXT_REPORTS")
    print("§KEYS in", filepath)
    keys = read_ODT_template(filepath)
    print("\n  ================================")
    print("\n -->", keys)

    fields = {
        "DATE_ISSUE": "21.06.2024",
        "FIRSTNAMES": "Fritz Alexander",
        "LASTNAME": "Steinkopf",
        "DATE_BIRTH": "01.04.2008",
        "CL": "10",
        "KK": "Kleinklassenzweig",
        "SYEAR": "2024 – 2025",
        "A": "",
        "L": "",
    }

    odt, m, u = write_ODT_template(filepath, fields)

    print("\n§MISSING:", m)
    print("\n§USED:", u)

    outpath = filepath.rsplit('.', 1)[0] + '_X.odt'
    with open(outpath, 'bw') as fh:
        fh.write(odt)
    print(" -->", outpath)

