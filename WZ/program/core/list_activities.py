"""
core/list_activities.py

Last updated:  2023-12-24

Present information on activities for teachers and classes/groups.
The information is formatted in pdf documents using the reportlab
library.
Also (unformatted) xlsx spreadsheets can be exported.

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
    # Enable package import if running as module
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, "TESTDATA"))

from core.base import Tr
T = Tr("core.list_activities")

### +++++

from typing import NamedTuple#, Optional
#from io import BytesIO

#import lib.pylightxl as xl
from fpdf import FPDF
#from fpdf.enums import TableBordersLayout
#from fpdf.fonts import FontFace

from core.base import (
    format_class_group,
    REPORT_CRITICAL,
    REPORT_ERROR,
    #DATAPATH,
)
from core.basic_data import CONFIG, get_database, print_fix
from core.classes import GROUP_ALL
from core.rooms import get_db_rooms, print_room_choice
from core.course_base import (
    filter_activities,
    workload_class,
    workload_teacher,
)

class COURSE_DATA(NamedTuple):
    """Encapsulate the data gathered for a course line by the function
    <teacher_table_data>.
    """
    class_groups: list[tuple[str, str, str]] # (CLASS, GROUP_TAG, class-name)
    subject: tuple[str, str]            # sid, full-name
    room: str                           # "user-friendly" string
    block_count: float
    pay: float
    colleagues: list[str]               # TID-list
    course_info: str
    report: str
    grades: str

class TEACHER_BLOCK(NamedTuple):
    """Encapsulate the data gathered for a teacher by the function
    <teacher_table_data>.
    """
    tid: str
    tname: str
    all_lessons: list[int]
    all_pay: float
    blocklist: list[tuple[str, str, list[int], list[COURSE_DATA]]]
    # items: (block-name, block-comment, lesson-list, course-list)
    noblocklist: list[tuple[list[int], list[COURSE_DATA]]]
    # items: (lesson-list, course-list)

### -----

class TeacherData(NamedTuple):
    klass: str
    block_subject: str
    block_tag: str
    subject: str
    group: str
    room: str
    lessons: str
    nlessons: int
    lesson_group: int
    lesson_data: int
    paynum: str     # for blocks/"Epochen" *can* be the number
    paystr: str
    pay: float


class ClassData(NamedTuple):
    subject: str
    group: str
    teacher_id: str
    block_subject: str
    block_tag: str
    lesson_group: int
    lesson_data: int
    room: str
    lessons: str
    nlessons: int
    paystr: str         #TODO: not reliable for pay if combined groups!


#?
def print_class_group(klass, group):
    """Return a representation of the class and group for the
    teacher-lists.
    If there is no group, return the class in brackets.
    If the group is the whole class, just return the class.
    Otherwise return the standard form for class + cgroup.
    """
    if group:
        if group == GROUP_ALL:
            return klass
        return class_group_join(klass, group)
    return f"({klass})"


def write_xlsx(xl_db, filepath):
    """Write a pylightxl "database" to the given path.
    """
    xl.writexl(db=xl_db, fn=filepath)


#TODO?
def make_teacher_table_xlsx(activities):
    headers = [
        "H_class",
        "H_block_subject",  # (name)
        "H_block_tag",
        "H_subject",        # (name)
        "H_group",
        "H_room",           # ($ not substituted)
        "H_units",          # list of lesson lengths
        "H_nunits",         # total number of lessons
        "H_lesson-group",   # Lesson-group-id
        "H_lesson-data",    # Lesson-data-id
        "H_npay",           # NLESSONS field
        "H_lessons",        # Pay calculation
        "H_pay",            # Pay units
    ]
    db = xl.Database()
    teachers = get_teachers()
    lg_ll = activities["Lg_LESSONS"]
    tmap = activities["T_ACTIVITIES"]
    for t in teachers:
        try:
            datalist = tmap[t]
        except KeyError:
            continue    # skip teachers without entries
        tname = teachers.name(t)
        items = teacher_list(datalist, lg_ll)
        # Add "worksheet" to table builder
        db.add_ws(ws=tname)
        sheet = db.ws(ws=tname)
        for col_id, field in enumerate(headers, start=1):
            sheet.update_index(row=1, col=col_id, val=T(field))
        # Add data to spreadsheet table
        row_id = 2
        pay_total = 0.0
        lesson_data_ids = set()
        for line in items:
            if line.lesson_data in lesson_data_ids:
                line = line._replace(paynum="", paystr="*", pay=0.0)
            else:
                lesson_data_ids.add(line.lesson_data)
                pay_total += line.pay
            for col_id, field in enumerate(line, start=1):
                sheet.update_index(row=row_id, col=col_id, val=field)
            row_id += 1
        # Total
        lastcol = len(headers)
        sheet.update_index(row=row_id, col=lastcol, val=pay_total)
        sheet.update_index(row=row_id, col=lastcol - 1, val=T("total"))
    return db

#TODO?
def make_class_table_xlsx(activities):
    db = xl.Database()
    headers = [
        "H_subject",
        "H_group",
        "H_teacher",
        "H_block_subject",
        "H_block_tag",
        "H_lesson-group",   # Lesson-group-id
        "H_lesson-data",    # Lesson-data-id
        "H_room",
        "H_units",
        "H_lessons"
    ]
    lg_ll = activities["Lg_LESSONS"]
    cmap = activities["C_ACTIVITIES"]
    for c in sorted(cmap):
        datalist = cmap[c]
        items = class_list(datalist, lg_ll)
        # Calculate the total number of lessons for the pupils.
        # The results should cover all (sub-)groups.
        # Each LESSON_GROUPS entry must be counted only once FOR
        # EACH GROUP, so keep track:
        lgsets = {}
        ag2lessons = {}
        class_groups = get_classes()[c].divisions
        g2ags = class_groups.group_atoms()
        no_subgroups = not g2ags
        if no_subgroups:
        # Add whole-class target
            ag2lessons[GROUP_ALL] = 0
            lgsets[GROUP_ALL] = set()
        else:
            for ag in class_groups.atomic_groups:
                ag2lessons[ag] = 0
                lgsets[ag] = set()
        # Add "worksheet" to table builder
        db.add_ws(ws=c)
        sheet = db.ws(ws=c)
        for col_id, field in enumerate(headers, start=1):
            sheet.update_index(row=1, col=col_id, val=T(field))
        row_id = 2
        for data in items:
            # Allocate the lessons to the minimal subgroups
            lg = data.lesson_group
            if (
                (g := data.group)
                and lg
                and (lessons := data.nlessons)
            ):
                if no_subgroups:
                    assert g == GROUP_ALL, (
                        f"group ({g}) lessons in class ({klass})"
                        " without subgroups???"
                    )
                    if lg in lgsets[GROUP_ALL]: continue
                    lgsets[GROUP_ALL].add(lg)
                    ag2lessons[GROUP_ALL] += lessons
                else:
                    ags = lgsets.keys() if g == GROUP_ALL else g2ags[g]
                    for ag in ags:
                        if lg in lgsets[ag]: continue
                        lgsets[ag].add(lg)
                        ag2lessons[ag] += lessons
            # Gather the display info for this line
            line = [
                data.subject,
                data.group,
                data.teacher_id,
                data.block_subject,
                data.block_tag,
                lg,
                data.lesson_data,
                data.room,
                data.lessons,
                data.paystr,
            ]
            for col_id, field in enumerate(line, start=1):
                sheet.update_index(row=row_id, col=col_id, val=field)
            row_id += 1
        # Collate the lesson counts
        if no_subgroups:
            results = [("", ag2lessons[GROUP_ALL])]
        else:
            # Simplify groups: seek primary groups which cover the various
            # numeric results
            # print("§ag2lessons:", ag2lessons)
            ln_lists = {}
            for ag, l in ag2lessons.items():
                try:
                    ln_lists[l].add(ag)
                except KeyError:
                    ln_lists[l] = {ag}
            results = []
            for l, agset in ln_lists.items():
                for g, ags in g2ags.items():
                    if set(ags) == agset:
                        results.append((g, l))
                        break
                else:
                    if set(class_groups.atomic_groups) == agset:
                        g = ""
                    else:
                        g = f"<{','.join(sorted(agset))}>"
                    results.append((g, l))
            results.sort()
        # Total
        lastcol = len(headers)
        for g, l in results:
            sheet.update_index(row=row_id, col=lastcol, val=l)
            sheet.update_index(
                row=row_id,
                col=lastcol - 1,
                val=g if g else T("total")
            )
            row_id += 1
    return db


#?
def make_teacher_table_room(activities):
    """Construct a pdf with a table for each teacher, each such table
    starting on a new page.
    The sorting within a teacher table is first class, then block,
    then subject.
    """
    def add_simple_items():
        for item in noblocklist:
            # The "team" tag is shown only when it is referenced later
            pdf.add_line(item)
        noblocklist.clear()

    headers = []
    colwidths = []
    for h, w in (
        ("H_team_tag",          15),
        ("H_group",             20),
        ("H_subject",           60),
        ("H_units",             35),
        ("H_room",              40),
    ):
        headers.append(T(h))
        colwidths.append(w)

    pdf = TablePages(
        title=T["teacher_activities"],
        author=CONFIG["SCHOOL_NAME"],
        headers=headers,
        colwidths=colwidths,
        align=((1, "l"), (2, "p")),
    )

    noblocklist = []
    teachers = get_teachers()
    lg_ll = activities["Lg_LESSONS"]
    tmap = activities["T_ACTIVITIES"]
    for t in teachers:
        try:
            datalist = tmap[t]
        except KeyError:
            continue    # skip teachers without entries
        tname = teachers.name(t)
        pdf.add_page(tname)
        items = teacher_list(datalist, lg_ll)
        lds = {} # for detecting parallel groups
        lesson_groups = set()
        pay_total = 0.0
        lessons_total = 0
        for item in items:
            ld = item.lesson_data
            if ld in lds:
                lds[ld] = 1
            else:
                lds[ld] = 0
                pay_total += item.pay
            if item.lesson_group not in lesson_groups:
                lesson_groups.add(item.lesson_group)
                lessons_total += item.nlessons
        pdf.add_text(
            f'{T("timetable_lessons")}: {lessons_total}'
        )
        pdf.add_vspace(5)

        klass = None
        for item in items:
            # The lesson-data-id is shown only when it is referenced later
            ld = item.lesson_data
            if lds[ld] > 0:
                # first time, show lesson-data-id
                w = f"[{ld}]"
                lds[ld] = -1
                ref = ""
                room = item.room
            elif lds[ld] < 0:
                ## second time, show reference to lesson-data-id
                ref = f"→ [{ld}]"
                w = ""
                room = ""
            else:
                ref = ""
                w = ""
                room = item.room

            if item.klass != klass:
                add_simple_items()
                # Add space before new class
                pdf.add_line()
                klass = item.klass

            # Combine class and group
            cg = print_class_group(item.klass, item.group)
            if item.block_subject:
                ## Add block item
                if ref:
                    t_lessons = ref
                else:
                    t_lessons = item.lessons
                    try:
                        n = int(item.paynum)
                        if (n > 0) and (n != item.nlessons):
                            t_lessons += f" [{n}]"
                    except ValueError:
                        pass
                pdf.add_line((
                    w,
                    cg,
                    f"{item.block_subject}::{item.subject}",
                    t_lessons,
                    room,
                ))
            else:
                noblocklist.append(
                    (w, cg, item.subject, ref or item.lessons, room)
                )
        if noblocklist:
            add_simple_items()
        # Add space before final underline
        pdf.add_line()
    return pdf.build_pdf()


def teacher_table_data():
    """Collect the lesson and pay data for each teacher, dividing the
    individual courses according to block.
    """
    db = get_database()
    lesson_units = db.table("LESSON_UNITS")
    # Needed for printing room lists:
    roomtable = db.table("TT_ROOMS")
    all_room_lists = get_db_rooms(
        db.table("ROOMS"), db.table("TT_ROOM_GROUP_MAP")
    )
    ### Collect the data for each teacher separately
    tlist = db.table("TEACHERS").teacher_list(skip_null = True)
    t_blocks = []
    for t, tid, tname in tlist:
        courses = filter_activities("TEACHER", t)
        ## Add the total lesson numbers
        all_lessons, all_pay  = workload_teacher(t, courses)
        #print("§teacher:", t, tid, tname, len(courses))
        block_map = {}
        noblocklist = []
        ## Sort according to block
        for cline in courses:
            course = cline.course
            cglist = []
            for gdata in cline.group_list:
                c = gdata.Class.CLASS
                g = gdata.GROUP_TAG
                id = gdata.Class.id
                cglist.append((c, g, id))
            tlist = []
            for tdata in cline.teacher_list:
                tid = tdata.Teacher.TID
                p = tdata.PAY_FACTOR
                id = tdata.Teacher.id
                tlist.append((tid, p, id))
            lb = course.Lesson_block
            lbid = lb.id
            block = course.Lesson_block.BLOCK
            ## Gather the lesson-block related info (lessons, workload, etc.)
            if block:
                # a named block
                try:
                    bname, bcomment = block.split("#", 1)
                except ValueError:
                    bname, bcomment = block, ""
                try:
                    blockdata = block_map[lbid]
                    llist = blockdata[2]
                except KeyError:
                    # first course for this block
                    llist = [
                        l.LENGTH
                        for l in lesson_units.get_block_units(lbid)
                    ]
                    blockdata = (bname, bcomment, llist, [])
                    block_map[lbid] = blockdata
            else:
                # not a named block
                llist = [
                    l.LENGTH
                    for l in lesson_units.get_block_units(lbid)
                ]
            ## Add the course data
            # workload/pay
            pay = 0.0
            colleagues = []
            _blocks = course.BLOCK_COUNT
            workload = lb.WORKLOAD
            if workload < 0.0:
                nlessons = sum(llist)
                workload = abs(workload * nlessons)
                block_count = T("WORKLOAD_LESSONS")
            else:
                block_count = f'[{print_fix(_blocks)}]'
            lfactor = workload * _blocks
            for tline in cline.teacher_list:
                if tline.Teacher.id == t:
                    pay = lfactor * tline.PAY_FACTOR
                    #print("§PAY:", tline.Teacher.TID, pay)
                else:
                    colleagues.append(tline.Teacher.TID)
            cg_list = [
                (cg.Class.CLASS, cg.GROUP_TAG, cg.Class.NAME)
                for cg in cline.group_list
            ]
            # The room is an ordered list of individual rooms
            # and an optional room-group.
            rlist = roomtable.get_room_list(course.id)
            croom = cline.get_classroom()
            # Show classroom instead of "$"
            rlist1 = []
            for r in rlist:
                if r.Room.id:
                    rlist1.append(r.Room.id)
                elif croom:
                    rlist1.append(croom)
                else:
                    REPORT_CRITICAL("Bug: no classroom")
            rxtra = course.Room_group
            #print("§get rooms:", rlist, "\n +++ ", rxtra)
            room = print_room_choice(
                room_choice = (rlist1, rxtra.id),
                room_lists = all_room_lists,
            )
            sbj = course.Subject
            course_data = COURSE_DATA(
                cg_list,
                (sbj.SID, sbj.NAME),
                room,
                block_count,
                pay,
                colleagues,
                course.INFO,
                course.REPORT,
                course.GRADES,
            )
            #print("$$$", course_data)
            if block:
                blockdata[3].append(course_data)
            else:
                noblocklist.append((llist, course_data))
        ## If there are entries, add data to teachers list
        if noblocklist or block_map:
            t_blocks.append(TEACHER_BLOCK(
                tid,
                tname,
                all_lessons,
                all_pay,
                sorted(block_map.values()),
                noblocklist
        ))
    return t_blocks


def make_teacher_table_pay(with_comments = True):
    """Construct a pdf with a table for each teacher, each such table
    starting on a new page.
    The courses are divided by block and sorted by subject and class-group.
    """
    headers = []
    colwidths = []
# Get column sizes from CONFIG?
    for h, w in (
        ("H_group",             20),
        ("H_subject",           60),
        ("H_room",              25),
        ("H_units",             30),
        ("H_pay",               20),
    ):
        headers.append(T(h))
        colwidths.append(w)
    pdf = FPDF()
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
#CONFIG?
    pdf.set_font("Times", size=12)
    ### Produce a table for each teacher
    t_blocks = teacher_table_data()
    for tdata in t_blocks:
        #print(f"\nTEACHER: {tdata.tname} ({tdata.tid})")
        pdf.add_page()
        pdf.set_font(style="b", size=16)
        pdf.start_section(f"{tdata.tname} ({tdata.tid})")
        pdf.write(text = f"{tdata.tname} ({tdata.tid})\n\n")
        pdf.set_font(size=12)
        ## Add the total lesson numbers
        #print(
        #    f"§workload: {tdata.all_lessons} lessons,"
        #    f" pay_quota = {tdata.all_pay}"
        #)
        #pdf.set_draw_color(200, 0, 0)
        pdf.set_draw_color(150) # grey-scale
        with pdf.table(
            width = 150,
            text_align = "CENTER",
            borders_layout = "HORIZONTAL_LINES",
            first_row_as_headings = False,
        ) as table:
            row = table.row()
            row.cell(
                T("timetable_lessons", n = tdata.all_lessons),
                align = "LEFT"
            )
            row.cell(
                T("pay_lessons", n = print_fix(tdata.all_pay)),
                align = "LEFT"
            )
            row = table.row()
            row.cell("")
            row.cell("")
        pdf.set_draw_color(0) # black
        with pdf.table(
            borders_layout = "SINGLE_TOP_LINE",
            col_widths = colwidths,
            padding = 1,
        ) as table:
            row = table.row()
            for h in headers:
                row.cell(h)

            ### Deal with the (named) blocks first
            for bname, bcomment, llist, clist in tdata.blocklist:
                row = table.row()
                row.cell(f"[[{bname}]]", colspan = 3)
                row.cell("; ".join(str(l) for l in llist))
                row.cell("")
                if with_comments and bcomment:
                    row = table.row()
                    row.cell(
                        T("BLOCK_COMMENT", comment = bcomment),
                        colspan = 5,
                        padding = (-2, 7, 1, 7)
                    )
                ## Show the individual courses, sorting by subject
                ## and class-group
                for cl in sorted(
                    clist,
                    key = lambda x: (x.subject[1], x.class_groups)
                ):
                    glist = [
                        format_class_group(g[0], g[1])
                        for g in cl.class_groups
                    ]
                    if glist:
                        # Use an extra line if multiple groups
                        if len(glist) > 1:
                            cg = "+++"
                            cgx = ", ".join(glist)
                        else:
                            cg = glist[0]
                            cgx = ""
                    else:
                        cg = "---"
                        cgx = ""
                    row = table.row()
                    row.cell(f' - {cg}')
                    row.cell(cl.subject[1])
                    row.cell(cl.room)
                    row.cell(cl.block_count)
                    row.cell(print_fix(cl.pay))
                    if cgx or cl.colleagues:
                        row = table.row()
                        row.cell(
                            T("MULTIGROUP", groups = cgx) if cgx else "",
                            colspan = 3,
                            padding = (-2, 7, 1, 7)
                        )
                        if cl.colleagues:
                            _clx = ", ".join(cl.colleagues)
                            clx = T("EXTRA_TEACHERS", teachers = _clx)
                        else:
                            clx = ""
                        row.cell(
                            clx,
                            colspan = 2,
                            padding = (-2, 7, 1, 7)
                        )
                    if with_comments and cl.course_info:
                        row = table.row()
                        row.cell(
                            T("COURSE_INFO", info = cl.course_info),
                            colspan = 5,
                            padding = (-2, 7, 1, 7)
                        )

            ### Now deal with non-block ("normal") lessons, sorting by
            ### subject and class-group
            for llist, cl in sorted(
                tdata.noblocklist,
                key = lambda x: (x[1].subject[1], x[1].class_groups)
            ):
                glist = [
                    format_class_group(g[0], g[1])
                    for g in cl.class_groups
                ]
                if glist:
                    # Use an extra line if multiple groups
                    if len(glist) > 1:
                        cg = "+++"
                        cgx = ", ".join(glist)
                    else:
                        cg = glist[0]
                        cgx = ""
                else:
                    cg = "---"
                    cgx = ""
                row = table.row()
                row.cell(cg)
                row.cell(cl.subject[1])
                row.cell(cl.room)
                row.cell("; ".join(str(l) for l in llist))
                row.cell(print_fix(cl.pay))
                if cgx or cl.colleagues:
                    row = table.row()
                    row.cell(
                        T("MULTIGROUP", groups = cgx) if cgx else "",
                        colspan = 3,
                        padding = (-2, 7, 1, 7)
                    )
                    if cl.colleagues:
                        _clx = ", ".join(cl.colleagues)
                        clx = T("EXTRA_TEACHERS", teachers = _clx)
                    else:
                        clx = ""
                    row.cell(
                        clx,
                        colspan = 2,
                        padding = (-2, 7, 1, 7)
                    )
                if with_comments and cl.course_info:
                    row = table.row()
                    row.cell(
                        T("COURSE_INFO", info = cl.course_info),
                        colspan = 5,
                        padding = (-2, 7, 1, 7)
                    )
    return pdf


def make_class_table_pdf(with_comments = True):
    headers = []
    colwidths = []
    for h, w in (
        ## Column widths in mm (for A4 portrait)
# Sizes -> CONFIG? Maybe not, why should these be configurable?
# Maybe a "low" level config?
        ("H_subject",           75),
        ("H_group",             20),
        ("H_teacher",           25),
        ("H_units",             30),
        ("H_lessons",           20),
    ):
        headers.append(T(h))
        colwidths.append(w)
    db = get_database()
    lesson_units = db.table("LESSON_UNITS")
    clist = db.table("CLASSES").class_list(skip_null = False)
    pdf = FPDF()
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
#TODO: Use CONFIG for the font?
#    pdf.add_font(
#        "droid-sans",
#        style = "",
#        fname = DATAPATH("CONFIG/DroidSans.ttf")
#    )
#    pdf.add_font(
#        "droid-sans",
#        style = "B",
#        fname = DATAPATH("CONFIG/DroidSansB.ttf")
#    )
#    pdf.set_font("droid-sans", size=12)
#    pdf.set_font("Helvetica", size=12)
    pdf.set_font("Times", size=12)
    ### Produce a table for each class
    for c, class_tag, class_name in clist:
        courses = filter_activities("CLASS", c)
        ## Sort according to blocks, grouping the courses belonging
        ## to a block ...
        block_map = {}
        noblock = []
        for cline in courses:
            block = cline.course.Lesson_block.BLOCK
            if block:
                try:
                    block_map[block].append(cline)
                except KeyError:
                    block_map[block] = [cline]
            else:
                noblock.append(cline)
        if block_map or noblock:
            #print("\nCLASS", class_tag)
            pdf.add_page()
            pdf.set_font(style="b", size=16)
            pdf.start_section(f"{class_name} ({class_tag})")
            pdf.write(text = f"{class_name} ({class_tag})\n\n")
            pdf.set_font(size=12)
            ## Add the total lesson numbers
            g_n_list = workload_class(c, courses)
            #print("§workload:", " ;  ".join(
            #    f"{g}: {n}" for g, n in g_n_list)
            #)
            #pdf.set_draw_color(200, 0, 0)
            pdf.set_draw_color(150) # grey-scale
            with pdf.table(
                width = 150,
                text_align = "CENTER",
                borders_layout = "HORIZONTAL_LINES",
                first_row_as_headings = False,
            ) as table:
                row = table.row()
                row.cell(T("total_lessons", align = "LEFT"))
                for g, n in g_n_list:
                    row.cell(f"{g}: {n}")
                if len(g_n_list) == 1:
                    row.cell("")
                row = table.row()
                row.cell("")
                for g, n in g_n_list:
                    row.cell("")
                if len(g_n_list) == 1:
                    row.cell("")
            pdf.set_draw_color(0) # black
            with pdf.table(
                borders_layout = "SINGLE_TOP_LINE",
                col_widths = colwidths,
                padding = 1,
            ) as table:
                row = table.row()
                for h in headers:
                    row.cell(h)
                ### First deal with the courses in (named) blocks
                for b in sorted(block_map):
                    clines = block_map[b]
                    # Need the lesson lengths
                    lb = clines[0].course.Lesson_block
                    lbid = lb.id
                    llist = [
                        l.LENGTH for l in lesson_units.get_block_units(lbid)
                    ]
                    try:
                        bname, bcomment = b.split("#", 1)
                    except ValueError:
                        bname, bcomment = b, ""
                    #print(f"  [[{bname}]] | {llist} | {sum(llist)}")
                    row = table.row()
                    row.cell(f"[[{bname}]]", colspan = 3)
                    row.cell("; ".join(str(l) for l in llist))
                    row.cell(str(sum(llist)))
                    # Could fetch all classes using the block, using
                    #    block_courses(block_id: int) -> list[COURSE_LINE]
                    # but it is probably not an essential piece of
                    # information
                    if with_comments and bcomment:
                        row = table.row()
                        row.cell(
                            T("BLOCK_COMMENT", comment = bcomment),
                            colspan = 5,
                            padding = (-2, 7, 1, 7)
                        )
                    ## Show the individual courses
                    for cl in clines:
                        glist = []
                        g0 = None
                        for g in cl.group_list:
                            if g.Class.id == c:
                                g0 = g.GROUP_TAG
                            else:
                                glist.append(
                                    format_class_group(
                                        g.Class.CLASS, g.GROUP_TAG
                                    )
                                )
                        if glist:
                            # Probably best to use abbreviated form in case
                            # the expanded form takes up too much space.
                            # The display of other class-groups is probably
                            # not so important anyway.
                            #g0 = f"{g0} + {', '.join(sorted(glist))}"
                            g0 = f"{g0}  ..."
                        row = table.row()
                        row.cell(f' - {cl.show("Subject")}')
                        row.cell(g0)
                        row.cell(cl.show("Teachers"))
                        if lb.WORKLOAD < 0.0:
                            block_count = T("WORKLOAD_LESSONS")
                        else:
                            _blocks = cl.course.BLOCK_COUNT
                            block_count = f'[{print_fix(_blocks)}]'
                        row.cell(block_count)
                        row.cell("")
                        if with_comments and cl.course.INFO:
                            row = table.row()
                            row.cell(
                                T("COURSE_INFO", info = cl.course.INFO),
                                colspan = 5,
                                padding = (-2, 7, 1, 7)
                            )
                ### Now deal with non-block ("normal") lessons
                for cl in noblock:
                    glist = []
                    g0 = None
                    for g in cl.group_list:
                        if g.Class.id == c:
                            g0 = g.GROUP_TAG
                        else:
                            glist.append(
                                format_class_group(
                                    g.Class.CLASS, g.GROUP_TAG
                                )
                            )
                    if glist:
                        g0 = f"{g0} + {', '.join(sorted(glist))}"
                    # Need the lesson lengths
                    lbid = cl.course.Lesson_block.id
                    llist = [
                        l.LENGTH for l in lesson_units.get_block_units(lbid)
                    ]
                    row = table.row()
                    row.cell(cl.show("Subject"))
                    row.cell(g0)
                    row.cell(cl.show("Teachers"))
                    row.cell("; ".join(str(l) for l in llist))
                    row.cell(str(sum(llist)))
                    if with_comments and cl.course.INFO:
                        row = table.row()
                        row.cell(
                            T("COURSE_INFO", info = cl.course.INFO),
                            colspan = 5,
                            padding = (-2, 7, 1, 7)
                        )
    return pdf


#TODO:
#EXPERIMENTAL: Getting data for reports (text & grade).
from core.teachers import Teachers
def report_data(GRADES = False):
    db = get_database()
    cgtable = db.table("COURSE_GROUPS")
    cttable = db.table("COURSE_TEACHERS")
    ## Iterate through all the courses, retaining only those with REPORT
    ## and GRADES entries – and groups and teachers!
    cg_reports = {}
    t_reports = {}
    for course in db.table("COURSE_BASE").records:
        ci = course.id
        if ci == 0: continue    # not a "real" COURSE_BASE entry
        if GRADES:
            if not course.GRADES:
                continue
        elif not course.REPORT:
            continue
        cglist = cgtable.get_course_groups(ci)
        sbj = course.Subject
        if not cglist:
            REPORT_ERROR(
                T("NO_GROUP", subject = sbj.NAME, id = ci)
            )
            continue
        tlist = cttable.get_course_teachers(ci)
        if not tlist:
            REPORT_ERROR(
                T("NO_TEACHER", subject = sbj.NAME, id = ci)
            )
            continue
        #s = (sbj.NAME, sbj.SID, sbj.id)

# class -> subject -> group -> teacher-list or teacher -> group-list ?
# teacher -> class -> subject -> group-list
# For the class grade tables, need class -> subject. The finer details
# may be relevant for access permissions, etc.
# For an individual teacher, need class -> subject. The finer details
# may be relevant for access permissions, etc.

        print("\n ***", sbj.NAME)
        for cg in cglist:
            print("cg:", cg.Class.CLASS, cg.GROUP_TAG)

        for t in tlist:
            print("t:", Teachers.get_name(t.Teacher))


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from ui.ui_base import SAVE_FILE

    report_data(GRADES = False)
    quit(1)

    pdf = make_teacher_table_pay()
    filepath = SAVE_FILE("pdf-Datei (*.pdf)", "Deputate")
    if filepath and os.path.isabs(filepath):
        if not filepath.endswith(".pdf"):
            filepath += ".pdf"
        pdf.output(filepath)
        print("  --->", filepath)

    pdf = make_class_table_pdf()
    filepath = SAVE_FILE("pdf-Datei (*.pdf)", "Klassen-Stunden")
    if filepath and os.path.isabs(filepath):
        if not filepath.endswith(".pdf"):
            filepath += ".pdf"
        pdf.output(filepath)
        print("  --->", filepath)

    quit(0)

    pdfbytes = make_teacher_table_room(activities)
    filepath = saveDialog("pdf-Datei (*.pdf)", "Lehrer-Stunden")
    if filepath and os.path.isabs(filepath):
        if not filepath.endswith(".pdf"):
            filepath += ".pdf"
        with open(filepath, "wb") as fh:
            fh.write(pdfbytes)
        print("  --->", filepath)

    pdfbytes = make_teacher_table_pay(activities)
    filepath = saveDialog("pdf-Datei (*.pdf)", "Deputate")
    if filepath and os.path.isabs(filepath):
        if not filepath.endswith(".pdf"):
            filepath += ".pdf"
        with open(filepath, "wb") as fh:
            fh.write(pdfbytes)
        print("  --->", filepath)

#    quit(0)

    cdb = make_class_table_xlsx(activities)
    filepath = saveDialog("Excel-Datei (*.xlsx)", "Klassen-Stunden")
    if filepath and os.path.isabs(filepath):
        if not filepath.endswith(".xlsx"):
            filepath += ".xlsx"
        xl.writexl(db=cdb, fn=filepath)
        print("  --->", filepath)

#    quit(0)

    tdb = make_teacher_table_xlsx(activities)
    filepath = saveDialog("Excel-Datei (*.xlsx)", "Deputate")
    if filepath and os.path.isabs(filepath):
        if not filepath.endswith(".xlsx"):
            filepath += ".xlsx"
        xl.writexl(db=tdb, fn=filepath)
        print("  --->", filepath)
