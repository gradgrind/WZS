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

#from core.wzbase import Tr
#T = Tr("text_report.covers")

### +++++

#from core.wzbase import DATAPATH, REPORT_ERROR
from core.wzbase import WZDatabase
from core.dates import print_date
from io_support.odt_support import write_ODT_template
from io_support.odf_pdf_merge import libre_office, merge_pdf

### -----


#TODO:
def make_covers(
    db: WZDatabase,
    class_id: int,
):
    ## Get class data:
    class_data = db.nodes[class_id]
    print("\n§class_data:", class_data)
    ## Get students' data:
    for sid in class_data["STUDENTS"]:
        print("  ++", db.nodes[sid])

    return

    students = db.table("STUDENTS")
    ## Report templates:
    _tinfo = db.table("GRADE_REPORT_CONFIG")._template_info
    template_info = {
        ti[0]: ti[1]
        for ti in _tinfo[occasion][class_group]
    }
    #print("\n§template_info:", template_info)
    ## Process each student
    results = []
    for line in grade_table.lines:
        st_id = line.student_id
        fields = {
            "SCHOOL": CONFIG.SCHOOL,
            "OCCASION": occasion,
        }
        fields.update(students.all_string_fields(st_id))
        cl_data = students[st_id].Class
        fields["CLASS"] = cl_data.CLASS
        fields["CLASS_YEAR"] = cl_data.YEAR
        fields["CLASS_NAME"] = cl_data.NAME
        values = line.values
        subject_map = {}
        for i, dci in enumerate(grade_table.column_info):
            if dci.TYPE == "GRADE":
                #print("???", dci)
                s = dci.DATA["SORTING"]
                v = values[i]
                if v == NO_GRADE:
                    continue
                val = (Subjects.clip_name(dci.LOCAL), v) #???
                try:
                    subject_map[s].append(val)
                except KeyError:
                    subject_map[s] = [val]
            else:
                fields[dci.NAME] = values[i]
        # Get template file
        try:
            ttype = fields["REPORT_TYPE"]
            tfile = template_info[ttype]
            if not tfile:
                continue
        except KeyError:
            continue
        template_file = DATAPATH(
            tfile,
            f"TEMPLATES/{CONFIG.GRADE_REPORT_TEMPLATES}"
        )
        if not template_file.endswith(".odt"):
            template_file = f"{template_file}.odt"
        #print("\n§template:", template_file)
        #print("§SUBJECT_MAP:", subject_map)
        for k, v in subject_map.items():
            v.reverse()
        #print("§SUBJECT_MAP_REVERSED:", subject_map)
        fields.update(CALENDAR.all_string_fields())
        #print("\n§FIELDS:", fields)
        # Make adjustments for specialities of the region or school-type
        local.reports.local_fields(fields)
        # Convert dates
        for f, val in fields.items():
            if f.startswith("DATE_"):
                if val:
                    try:
                        dateformat = CONFIG.GRADE_DATE_FORMAT
                    except KeyError:
                        dateformat = None
                    #print("§dateformat:", dateformat, val)
                    val = print_date(val, dateformat)
                fields[f] = val
        #print("\n$$$", fields)

        g_pending = None
        odt, m, u = write_ODT_template(template_file, fields, special)
        # If there are still entries in <subject_map> at the end of
        # the processing, these are unplaced values – report them.
        xs_subjects = []
        for sg in subject_map.values():
            xs_subjects += [ f"  -- {s}: {g}" for s, g in sg ]
        if xs_subjects:
            REPORT_ERROR(T("EXCESS_SUBJECTS", slist = "\n".join(xs_subjects)))

        results.append((odt, fields["SORTNAME"], ttype))

        #print("\n§MISSING:", m)
        #print("\n§USED:", u)

    return results


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.wzbase import DATAPATH
    from w365.read_w365 import read_w365

    #w365path = DATAPATH("test.w365", "w365_data")
    #w365path = DATAPATH("fwsb.w365", "w365_data")
    #w365path = DATAPATH("fms.w365", "w365_data")
    w365path = DATAPATH("fwsb2.w365", "w365_data")

    #w365path = DATAPATH("fms_xep.w365", "w365_data")

    print("W365 FILE:", w365path)

    w365db = read_w365(w365path)

    print("§CLASSES:", w365db.node_tables["CLASSES"])
    cid = w365db.node_tables["CLASSES"][0]
    make_covers(w365db, cid)

    quit(2)

    _o = "1. Halbjahr"
    _cg = "12G.R"
    #_cg = "12G.G"
    #_cg = "13"
    #_cg = "11G"
    outdir = DATAPATH(f"{_o}/{_cg}".replace(" ", "_"), "working_data")
    print("§outdir", outdir)
    pdf_dir = os.path.join(outdir, "pdf")
    os.makedirs(pdf_dir, exist_ok = True)
    odt_list = []
    for odt, sname, ttype in make_grade_reports(_o, _cg):
        outpath = os.path.join(outdir, sname) + ".odt"
        with open(outpath, 'bw') as fh:
            fh.write(odt)
        print(" -->", outpath)
        odt_list.append(outpath)
#TODO: clear pdf folder?
    libre_office(odt_list, pdf_dir, show_output = True)

    pdf_list = [
        os.path.join(pdf_dir, f)
        for f in sorted(os.listdir(pdf_dir))
        if f.endswith(".pdf")
    ]
    pdf_path = os.path.join(outdir, f"{_o}-{_cg}.pdf".replace(" ", "_"))
    merge_pdf(pdf_list, pdf_path)
    print(" PDF:->", pdf_path)
