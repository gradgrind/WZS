"""
tables/table_utilities.py

Last updated:  2024-01-12

Support functions for various table-based operations.

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
    #from core.base import setup
    #setup(os.path.join(basedir, 'TESTDATA'), debug = True)

#from core.base import Tr
#T = Tr("tables.table_utiities")

### +++++

from html.parser import HTMLParser

from core.base import REPORT_CRITICAL

### -----

### Conversion functions between lists of lists and tab-separated-values
### strings

def TSV2Table(text:str) -> list[list[str]]:
    """Parse a "tsv" (tab separated value) string into a list of lists
    of strings (a "table").

    The input text is tabulated using tabulation characters to separate
    the fields of a row and newlines to separate columns.

    This can cope with various forms of newlines.
    """
    # 'splitlines' normally strips a trailing newline, so add one
    # before splitting.
    rows = (text + "\n").splitlines()
    return [
        row.split("\t")
        for row in rows
    ]


def ToRectangle(table: list[list[str]], test_only: bool = False) -> int:
    """Extend shorter rows with empty fields ("") so that all rows
    have the same length.
    Perform the operation "in place", return the number of added cells.
    If <test_only> is true, no changes will be made, just the number
    of changes necessary will be returned.
    """
    max_len = 0
    for row in table:
        if (l := len(row)) > max_len:
            max_len = l
    changes = 0
    for row in table:
        if (n := max_len - len(row)) > 0:
            if not test_only:
                row += [""] * n
            changes += n
    return changes


def Table2TSV(table):
    """Represent a list of lists of strings (a "table") as a "tsv"
    (tab separated value) string.
    The lines are separated by "\r\n".
    """
    return "\r\n".join(["\t".join(row) for row in table])

def html2Table(html: str) -> list[list[str]]:
    """Parse html to extract a table. It assumes there is at most one
    table in the html – multiple tables will be concatenated.
    Return a list of string lists.

    This function is useful for pasting tabular data, in particular
    from LibreOffice, whose clipboard output is primarily HTML.
    In this case, reading the clipboard as text can lead to data loss.
    """
    tp = __TableParser()
    return tp.parse(html)
#+
class __TableParser(HTMLParser):
    """Support class for <html2Table>.
    Create an instance of this class and then call the <parse>
    method to read a table as a list of lists from the html input.
    """
    def parse(self, html):
        """This is the main function.
        """
        self.table_rows = []
        self.table_cols = None
        self.data_tag = None
        self.feed(html)
        return self.table_rows

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.table_cols = []
            self.table_rows.append(self.table_cols)
        elif tag == "td":
            self.data_tag = []

    def handle_endtag(self, tag):
        if tag == "tr":
            self.table_cols = None
        elif tag == "td":
            if self.data_tag:
                if len(self.data_tag) != 1:
                    REPORT_CRITICAL(
                        "Bug, unexpected multiple data fields in <td>:\n"
                        f"  {self.data_tag}"
                    )
                self.table_cols.append("".join(self.data_tag))
            else:
                self.table_cols.append("")

    def handle_data(self, data):
        if self.data_tag is not None:
            self.data_tag.append(data)


def pasteFit(
    table_data: list[list[str]],
    nrows: int,
    ncols: int
) -> bool:
    """Adjust rectangular paste data (strings only) to fit the
    cell range – also rectangular, but perhaps with different
    dimensions – into which it is to be pasted.

    Pasting to more than one selected cell is possible if the data
    to be pasted has "compatible" dimensions:
        - A single cell can be pasted to any block.
        - A single row of cells can be pasted to a block of cells with
          the same width.
        - A single column of cells can be pasted to a block of cells
          with the same height.
        - Otherwise a block of cells can only be pasted to a block of
          cells with the same dimensions.

    Perform the operation "in place", return <True> if successful.
    """
    print("%%% IN:", table_data)
    paste_rows = len(table_data)
    row0 = table_data[0]
    paste_cols = len(row0)
    if paste_rows == 1:     # paste a single row
        if paste_cols == 1: # paste a single cell
            print("%%% 1 cell")
            row0 *= ncols   # copy value for each column
        elif paste_cols != ncols:
            return False
        print("%%% 1 row")
        table_data *= nrows
        return True
    if paste_cols == 1:     # paste a single column
        if paste_rows != nrows:
            return False
        print("%%% 1 column")
        # copy the column
        for r in table_data:
            r *= ncols
        return True
    # paste a block
    print("%%% test block")
    return paste_rows == nrows and paste_cols == ncols


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    html = """
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
    <html>
    <head>

            <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
            <title></title>
            <meta name="generator" content="LibreOffice 7.0.4.2 (Linux)"/>
            <style type="text/css">
                    body,div,table,thead,tbody,tfoot,tr,th,td,p { font-family:"Liberation Sans"; font-size:x-small }
                    a.comment-indicator:hover + comment { background:#ffd; position:absolute; display:block; border:1px solid black; padding:0.5em;  }
                    a.comment-indicator { background:red; display:inline-block; border:1px solid black; width:0.5em; height:0.5em;  }
                    comment { display:none;  }
            </style>
    </head>
    <body>
    <table cellspacing="0" border="0">
            <colgroup span="2" width="107"></colgroup>
            <tr>
                    <td height="21" align="left"><br></td>
                    <td align="left"><br></td>
            </tr>
            <tr>
                    <td height="21" align="left">A</td>
                    <td align="left">B</td>
            </tr>
            <tr>
                    <td height="21" align="left"><br></td>
                    <td align="left"><br></td>
            </tr>
    </table>
    </body>
    </html>
    """
    print("Parse paste data (html):\n  ", html2Table(html))
    t = []
    print("\n ============================\n")
    print("ToRectangle TABLE:", t)
    print("  ... CHANGES:", ToRectangle(t))
    print("  ->", t)
    t = [["", "1"], ["A", "B", "C"], []]
    print("ToRectangle TABLE:", t)
    print("  ... CHANGES:", ToRectangle(t))
    print("  ->", t)

    print("\n ============================\n")
    print("FIT 3x3?", pasteFit(t, 3, 3))
    print("FIT 2x3?", pasteFit(t, 2, 3))

    r = 5
    c = 3
    print(f"\nPASTE AREA: {r}x{c}:")
    t = [["A", "B", "C"]]
    print("  TABLE:", t)
    if pasteFit(t, r, c):
        print("    -->", t)
    else:
        print("    Fail")
    t = [["A", "B", "C"]]
    print("  +++ in 5x6?", pasteFit(t, 5, 6))
    t = [["A"], ["B"], ["C"], ["D"], ["E"]]
    print("  TABLE:", t)
    if pasteFit(t, r, c):
        print("    -->", t)
    else:
        print("    Fail")
    t = [["A"], ["B"], ["C"], ["D"], ["E"]]
    print("  +++ in 6x1?", pasteFit(t, 6, 1))
    t = [["A"]]
    print("  TABLE:", t)
    if pasteFit(t, r, c):
        print("    -->", t)
    else:
        print("    Fail")
    t = [["A"]]
    print("  +++ in 1x1?", pasteFit(t, 1, 1))
    print("     -->", t)
