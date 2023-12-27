"""
grades/grade_tables.py - last updated 2023-12-27

Manage grade tables.


=+LICENCE=================================
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
=-LICENCE=================================
"""

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import Tr
T = Tr("grades.grade_tables")

### +++++

from core.base import REPORT_ERROR, REPORT_WARNING
from core.basic_data import CALENDAR
from core.list_activities import report_data

### -----

def make_grade_table(template, data, grades = None) -> bool:
    """Build a basic pupil/subject table for grade input using a
    template appropriate for the given group.
    If grades are supplied, fill the table with these.
    Return true if successfully completed.
    """
    info = {
        "+1": CALENDAR.SCHOOL_YEAR, # e.g. "2024"
        "+2": data["CLASS_GROUP"],  # e.g. "12G.R"
        "+3": data["OCCASION"],     # e.g. "2. Halbjahr", "Abitur", etc.
    }
    print("§info:", info)
    template.setInfo(info)


    for min_width, val in enumerate(template.rows[0]):
        if val and min_width > 10:
            break
    else:
        REPORT_WARNING(T("NO_MIN_COL", path = template.template))
    print("$:", min_width)

#    return

# Sorting??? (on SORTING and NAME?)
    ### Go through the template columns and check if they are needed:
    rowix: list[int] = template.header_rowindex  # indexes of header rows
    if len(rowix) != 2:
        REPORT_ERROR(T("TEMPLATE_HEADER_WRONG", path = template.template))
        return False
    sidcol: list[tuple[str, int]] = []
    sid: str
    for sbj in data["SUBJECTS"]:
        # Add subject
#TODO: DO I rather want the db id?
        sid = sbj.SID
        col: int = template.nextcol()
        sidcol.append((sid, col))
        template.write(rowix[0], col, sid)
        template.write(rowix[1], col, sbj.NAME)
    # Enforce minimum number of columns
    while col < min_width:
        col = template.nextcol()
        template.write(rowix[0], col, "")
    # Delete excess columns
    template.delEndCols(col + 1)
    return True


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import DATAPATH

    '''
    configfile = DATAPATH("CONFINI.ini", "TEMPLATES")
    print("§§§§", configfile)

    import configparser
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'ServerAliveInterval': '45',
                     'Compression': 'yes',
                     'CompressionLevel': '9'}
    config['forge.example'] = {}
    config['forge.example']['User'] = 'hg'
    config['topsecret.server.example'] = {}
    topsecret = config['topsecret.server.example']
    topsecret['Port'] = '50022'     # mutates the parser
    topsecret['ForwardX11'] = 'no'  # same here
    config['DEFAULT']['ForwardX11'] = 'yes'
    config['DEFAULT']['MULTILINE'] = 'Line1\nLine2\n\ \ Indented'
    with open(configfile, 'w') as fh:
        config.write(fh)

    ...

    config.read(configfile)
    print(config["DEFAULT"]["MULTILINE"])
    '''

    from core.basic_data import get_database
    from tables.matrix import ClassMatrix

    db = get_database()

    ctable = db.table("CLASSES")
    c_reports, t_reports = report_data(GRADES = True)
    for c, items in c_reports.items():
        print("\n***", ctable[c].CLASS)
        for item in items:
            print("  --",
                item[0],
                item[1],
                item[2],
                ", ".join(t.Teacher.TID for t in item[3])
            )

#    quit(2)

    filepath = DATAPATH("NOTEN_SEK_I", "TEMPLATES")
    template = ClassMatrix(filepath)

    smap = {}
    for s in c_reports[21]:
        sdata = s[0]
#        slist.append((sdata.SORTING, sdata.NAME, sdata.sid, sdata.id))
#        slist.sort()
        smap[sdata.id] = sdata
        slist = sorted(smap.values(), key = lambda x: (x.SORTING, x.NAME))


    make_grade_table(
        template,
        data = {
            "CLASS_GROUP": "11G",
            "OCCASION": "1. Halbjahr",
            "SUBJECTS": slist,
        },
    )

    print(" ->", template.save(filepath + "__test1"))
