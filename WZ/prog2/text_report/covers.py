"""
text_report/covers.py - last updated 2024-05-04

Use odt-documents (ODF / LibreOffice) as templates for report covers.


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

from core.wzbase import WZDatabase, REPORT_ERROR, REPORT_INFO
from core.dates import print_date
from io_support.odt_support import write_ODT_template
from io_support.odf_pdf_merge import libre_office, merge_pdf

### -----


#TODO: ASCII-only result? Handle tussenvoegsel? Put it in its own module.
def sort_name(fields: dict[str, str]) -> str:
    ln = "_".join(fields["LASTNAME"].split())
    fn = "_".join(fields["FIRSTNAME"].split())
    return f"{ln}_{fn}"


def make_covers_odt(
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
    #print("§template:", template_file)

    ## Process each student
    results = []
    for sid in class_data["STUDENTS"]:
        sdata = db.nodes[sid]
        fields = {
            "SCHOOL": db.config["SCHOOL"],
            "SYEAR": db.config["SCHOOL_YEAR"],
            "DATE_ISSUE": extra["DATE_ISSUE"],
            "CL": class_data["ID"],
            "A": "",
            "L": "",
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

        odt, m, u = write_ODT_template(template_file, fields)
        results.append((sort_name(fields), odt))

        #print("\n§MISSING:", m)
        #print("\n§USED:", u)

    return results




def save_reports(folder: str, klass, reports: list):
    odt_dir = os.path.join(folder, klass)
    pdf_dir = os.path.join(odt_dir, "pdf")
    #print("§pdf_dir:", pdf_dir)
    os.makedirs(pdf_dir, exist_ok = True)
    odt_list = []
    pdf_list0 = []
    for sname, odt in sorted(reports):
        outpath = os.path.join(odt_dir, sname) + ".odt"
        with open(outpath, 'bw') as fh:
            fh.write(odt)
        #print(" -->", outpath)
        odt_list.append(outpath)
        pdf_list0.append(os.path.join(pdf_dir, f"{sname}.pdf"))
    # Clear pdf folder
    for f in os.listdir(pdf_dir):
        os.remove(os.path.join(pdf_dir, f))
    # Generate pdf files
    libre_office(odt_list, pdf_dir, show_output = True)
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
        reports = make_covers_odt(w365db, cid, {"DATE_ISSUE": issue})
        clnode = w365db.nodes[cid]
        print(f'\nREPORT COVERS for class {clnode["ID"]}:')
        cl, cx = clnode["SORTING"]
        save_reports(
            w365db.data_path(
                "working_data",
                "REPORT_COVERS",
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
