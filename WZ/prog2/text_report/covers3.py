"""
typt_report/covers3.py - last updated 2024-05-10

Use typst templates for report covers.


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

from core.wzbase import WZDatabase, REPORT_ERROR, REPORT_INFO, REPORT_OUT
from core.dates import print_date
from io_support.odf_pdf_merge import run_extern, merge_pdf

REGEX = re.compile(r"\{\{(.*?)\}\}")

### -----


#TODO: ASCII-only result? Handle tussenvoegsel? Put it in its own module.
def sort_name(fields: dict[str, str]) -> str:
    ln = "_".join(fields["LASTNAME"].split())
    fn = "_".join(fields["FIRSTNAME"].split())
    return f"{ln}_{fn}"


def run_typst(typ_list, pdf_dir, root_dir, show_output = False):
    """Convert a list of typst-files to pdf-files.
    The input files are provided as a list of absolute paths,
    <pdf_dir> is the absolute path to the output folder.
    If <show_output> is true, the processing output will be displayed.
    """
    def extern_out(line):
        if show_output:
            REPORT_OUT(line)
    for tfile in typ_list:
        fout = os.path.basename(tfile).rsplit(".", 1)[0]
        pdfout = os.path.join(pdf_dir, fout + ".pdf")
        rc, msg = run_extern(
#TODO
#            SYSTEM["TYPST"],
            "typst",
            "compile",
            "--root",
            root_dir,
            tfile,
            pdfout,
            feedback = extern_out
        )


#TODO: Handle newline in field values
#TODO: Other typt manipulations, say conditionals, loops, ...
def write_template(
    template: str,
    fields: dict[str, str],
    special = None
) -> tuple[str, dict[str, int], dict[str, str]]:
    """Read the contents of the document seeking special typt fields.
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
            typt = fields[k]
        except KeyError:
            try:
                typt = special(k)
            except TypeError:
                typt = None
            if typt is None:
                try:
                    missing[k] += 1
                except KeyError:
                    missing[k] = 1
                typt = "???"
        else:
            try:
                used[k] += 1
            except KeyError:
                used[k] = 1
        return typt

    typt = REGEX.sub(fsub, template)
    return typt, missing, used


def make_covers(
    db: WZDatabase,
    class_id: int,
    extra: dict[str, str],
):
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
    template_file = db.data_path("TEST_COVER", "COVER",)
    if not template_file.endswith(".typ"):
        template_file += ".typ"
    #print("§template:", template_file)
    with open(template_file, "r", encoding = "utf-8") as fh:
        template = fh.read()

    ## Process each student
    results = []
    for sid in class_data["STUDENTS"]:
        sdata = db.nodes[sid]
        fields = {
            "SCHOOL": db.config["SCHOOL"],
            "SYEAR": db.config["SCHOOL_YEAR"],
            "DATE_ISSUE": extra["DATE_ISSUE"],
            "CL": class_data["ID"],
#TODO: These fields are available in case they should be automated at
# some point ...
            "A": "",
            "L": "",
            "B": "",
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

        typt, m, u = write_template(template, fields)
        results.append((sort_name(fields), typt))

        #print("\n§MISSING:", m)
        #print("\n§USED:", u)

    return results


def save_reports(folder: str, klass, reports: list):
    in_dir = os.path.join(folder, klass)
    pdf_dir = os.path.join(in_dir, "pdf")
    #print("§pdf_dir:", pdf_dir)
    os.makedirs(pdf_dir, exist_ok = True)
    in_list = []
    pdf_list0 = []
    for sname, text in sorted(reports):
        outpath = os.path.join(in_dir, sname) + ".typ"
        with open(outpath, 'w') as fh:
            fh.write(text)
        #print(" -->", outpath)
        in_list.append(outpath)
        pdf_list0.append(os.path.join(pdf_dir, f"{sname}.pdf"))
    # Clear pdf folder
    for f in os.listdir(pdf_dir):
        os.remove(os.path.join(pdf_dir, f))
    # Generate pdf files
    run_typst(in_list, pdf_dir, root_dir = folder, show_output = True)
    # Merge pdf files
    pdf_list = []
    for f in pdf_list0:
        if os.path.exists(f):
            pdf_list.append(f)
        else:
            REPORT_ERROR(T("MISSING_PDF", path = f))
    pdf_path = os.path.join(folder, f"{klass}.pdf")
    merge_pdf(pdf_list, pdf_path)
    REPORT_INFO(f" PDF:-> {pdf_path}")


def make_all_covers(w365db, class_ids, issue):
    for cid in class_ids:
        reports = make_covers(w365db, cid, {"DATE_ISSUE": issue})
        clnode = w365db.nodes[cid]
        print(f'\nREPORT COVERS for class {clnode["ID"]}:')
        cl, cx = clnode["SORTING"]
        save_reports(
            w365db.data_path(
                "working_data",
                "_REPORT_COVERS",
            ),
            f"{cl:02}{cx}",
            reports
        )


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
        issue= "2024-06-21"
    )
