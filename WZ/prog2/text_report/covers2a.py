"""
text_report/covers2a.py - last updated 2024-05-10

Use xetex templates for report covers - using one file per class.


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
    from core.wzbase import setup
    setup(basedir)

from core.wzbase import Tr
T = Tr("text_report.covers")

### +++++

import re
import shutil

from core.wzbase import WZDatabase, REPORT_ERROR, REPORT_INFO, REPORT_OUT
from core.dates import print_date
from io_support.odf_pdf_merge import run_extern, merge_pdf

REGEX = re.compile(r"\[\[(.*?)\]\]")

### -----


#TODO: ASCII-only result? Handle tussenvoegsel? Put it in its own module.
def sort_name(fields: dict[str, str]) -> str:
    ln = "_".join(fields["LASTNAME"].split())
    fn = "_".join(fields["FIRSTNAME"].split())
    return f"{ln}_{fn}"


def run_tex(tex_file, pdf_dir, show_output = False):
    """Convert a tex-file to pdf.
    The input file is provided as an absolute path,
    <pdf_dir> is the absolute path to the output folder.
    If <show_output> is true, the processing output will be displayed.
    """
    def extern_out(line):
        if show_output:
            REPORT_OUT(line)

    rc, msg = run_extern(
#TODO
#            SYSTEM["TEX"],
        "xelatex",
        "-interaction=nonstopmode",
        f"-output-directory={pdf_dir}",
        tex_file,
        feedback = extern_out
    )

    fname = os.path.basename(tex_file).rsplit(".", 1)[0]
    file_base = os.path.join(pdf_dir, fname)
    if os.path.isfile(f"{file_base}.pdf"):
        os.remove(f"{file_base}.aux")
        os.remove(f"{file_base}.log")


#TODO: Handle newline in field values
#TODO: Other text manipulations, say conditionals, loops, ...
def write_template(
    template: str,
    units: list[dict[str, str]],
    special = None
) -> tuple[str, dict[str, int], dict[str, str]]:
    """Read the contents of the document seeking special text fields.
    These are delimited by [[ and ]].
    Substitute these by the values supplied in <fields>.
    <units> is a list of mappings, one for each individual rport which
    is to be combined into one tex input file. The mappings specify the
    values to be placed in the specially marked fields.
    <special> is an optional function for replacing keys which are not
    in <fields>. It returns <None> if it receives a key it cannot handle.
    Return three items:
        - The modified file (bytes),
        - non-substituted fields in the document:
            mapping, field -> number of occurrences,
        - used entries in <fields>:
            mapping, field -> number of replacements.
    """
    keys = {}
    missing = {}
    used = {}

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

    ### Parse the template
    lines0 = []
    block = []
    block_link = []
    lines1 = []
    iterlines = iter(template.splitlines())
    try:
        while True:
            line = next(iterlines)
            if line.lstrip().startswith("%%++"):
                break
            lines0.append(line)
    except StopIteration:
        ### End of input – no block
        if len(units) > 1:
#TODO
            REPORT_ERROR("UNITS_BUT_NO_BLOCK")
            return None
        fields = units[0]
        text = REGEX.sub(fsub, "\n".join(lines0))
        return text, missing, used

    # repeatable block
    try:
        while True:
            line = next(iterlines)
            if line.lstrip().startswith("%%--"):
                break
            block.append(line)
    except StopIteration:
#TODO end of input – no block linkage
        REPORT_ERROR("NO_END_OF_BLOCK (%%--)")
        return None
    # End of block
    if not block:
        REPORT_ERROR("EMPTY_BLOCK")
        return None
    try:
        while True:
            line = next(iterlines)
            if line.lstrip().startswith("%%.."):
                break
            block_link.append(line)
    except StopIteration:
#TODO end of input – no block linkage
        REPORT_ERROR("NO_BLOCK_LINKAGE (%%..)")
        return None
    # End of block linkage
    try:
        while True:
            lines1.append(next(iterlines))
    except StopIteration:
        # end of input
        pass

    ### Construct the blocks and put the parts together
    pre = "\n".join(lines0)
    body = "\n".join(block)
    linkage = "\n".join(block_link)
    post = "\n".join(lines1)

    blist = []
    for fields in units:
        if blist:
            blist.append(linkage)
        blist.append(REGEX.sub(fsub, body))
    text = "\n".join([pre] + blist + [post])
    return text, missing, used


def make_covers(
    db: WZDatabase,
    class_id: int,
    extra: dict[str, str],
) -> str:
    ## Get class data:
    class_data = db.nodes[class_id]
    #print("\n§class_data:", class_data)

    ## Report template:
    k0, k1 = class_data["SORTING"]
    try:
        t = db.config[f"REPORT_COVER_{k0}_{k1}"]
    except KeyError:
        t = db.config[f"REPORT_COVER_*_{k1}"]
    template_file = db.data_path("TEMPLATES", "REPORTS", t)
#TODO: Set up template loading properly
#TODO: Handle the various types of template / result
#TODO: Maybe the logo should be at a relative path?
    logo = db.data_path("TEST_COVER", "fwsb-logo.pdf")
    template_file = db.data_path("TEST_COVER", "COVER",)
    if not template_file.endswith(".tex"):
        template_file += ".tex"
    #print("§template:", template_file)
    with open(template_file, "r", encoding = "utf-8") as fh:
        template = fh.read()

    ## Collect data for each student
    units = []
#TODO: The students need sorting!
    for sid in class_data["STUDENTS"]:
        sdata = db.nodes[sid]
        fields = {
            "LOGO": logo,
            "SCHOOL": db.config["SCHOOL"],
            "SYEAR": db.config["SCHOOL_YEAR"],
            "DATE_ISSUE": extra["DATE_ISSUE"],
            "CL": class_data["ID"],
            # These need some "text" or else the boxes collapse.
            # The text can, however, be invisible.
#TODO: These fields are available in case they should be automated at
# some point ...
            "A": r"\phantom{1}",
            "L": r"\phantom{1}",
            "B": r"\phantom{1}",
        }
        fields.update(sdata.data)
        #print("  ++", fields)

        ## Convert dates
        for f, val in fields.items():
            if f.startswith("DATE_"):
                if val:
                    dateformat = db.config["FORMAT_DATE"]
                    #print("§dateformat:", dateformat, val)
                    val = print_date(val, dateformat)
                fields[f] = val
        #print("\n$$$", fields)
        units.append(fields)
    text, m, u = write_template(template, units)

    #print("\n§MISSING:", m)
    #print("\n§USED:", u)

    return text


def make_all_covers(w365db, class_ids, issue):
    save_path = w365db.data_path(
        "working_data",
        "_REPORT_COVERS",
    )
    # Clear / create result folder
    try:
        shutil.rmtree(save_path)
    except FileNotFoundError:
        pass
    for cid in class_ids:
        cin = make_covers(w365db, cid, {"DATE_ISSUE": issue})
        clnode = w365db.nodes[cid]
        print(f'\nREPORT COVERS for class {clnode["ID"]}:')
        cl, cx = clnode["SORTING"]
        klass = f"{cl:02}{cx}"
        tex_dir = os.path.join(save_path, klass)
        tex_file = os.path.join(tex_dir, f"{klass}.tex")
        os.makedirs(tex_dir)
        # Generate pdf file
        with open(tex_file, "w", encoding = "utf-8") as fh:
            fh.write(cin)
        run_tex(tex_file, save_path, show_output = True)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.wzbase import DATAPATH
    from w365.read_w365 import read_w365

    w365path = DATAPATH("fwsb2.w365", "w365_data")
    w365path = DATAPATH("Current.w365", "w365_data")

    print("W365 FILE:", w365path)

    w365db = read_w365(w365path)

    #print("§CLASSES:", w365db.node_tables["CLASSES"])
    make_all_covers(
        w365db,
        w365db.node_tables["CLASSES"],
        issue = "2024-06-21"
    )
