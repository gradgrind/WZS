"""
grades/gradetable.py

Last updated:  2023-06-16

Access grade data, read and build grade tables.

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

# Bear in mind that a pupil's groups and "level" can change during a
# school-year. Thus these fields are saved along with the grades when
# grade reports are built and issued. After a set of grade reports has
# been issued, subsequent inspection of the data for this issue should
# show the state at the time of issue. Inspection and editing prior to
# the date of issue should update to the latest database state of the
# pupils.

###############################################################

import sys, os

if __name__ == "__main__":
    import locale

    print("LOCALE:", locale.setlocale(locale.LC_ALL, ""))
    # Enable package import if running as module
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import start

    #    start.setup(os.path.join(basedir, "TESTDATA"))
    start.setup(os.path.join(basedir, "DATA-2023"))

T = TRANSLATIONS("grades.grades_base")

### +++++

from typing import Optional
import datetime

from core.base import class_group_split, Dates
from core.db_access import (
    db_read_table,
    read_pairs,
    db_new_row,
    db_delete_rows,
    db_update_field,
    write_pairs_dict,
)
from core.basic_data import SHARED_DATA
from core.pupils import pupil_name, pupil_data
from core.report_courses import get_pupil_grade_matrix
from tables.spreadsheet import read_DataTable
from tables.matrix import KlassMatrix
from local.grade_processing import GradeFunction

NO_GRADE = "–"  # shown in cells which are not defined for a pupil ...
# e.g. subjects not taken (NOT stored in the database)

### -----


def GetGradeConfig():
    """Fetch the base configuration data for grade handling. The
    resulting mapping is cached.
    """
    try:
        return SHARED_DATA["GRADES_BASE"]
    except KeyError:
        pass
    path = DATAPATH("CONFIG/GRADES_BASE")
    data = MINION(path)
    data["__PATH__"] = path
    SHARED_DATA["GRADES_BASE"] = data
    return data


def get_occasions_groups():
    """Get a list of occasions and for each occasion a list of groups
    which have an entry of that occasion. The result is cached.
    """
    try:
        return SHARED_DATA["GRADES_OCCASIONS_GROUPS"]
    except KeyError:
        pass
    occasions = {}
    SHARED_DATA["GRADES_OCCASIONS_GROUPS"] = occasions
    grade_config = GetGradeConfig()
    for group, gocclist in grade_config["GROUP_DATA"].items():
        for occ, odata in gocclist:
            try:
                ogd = occasions[occ]
            except KeyError:
                occasions[occ] = {group: odata}
            else:
                if group in ogd:
                    REPORT(
                        "ERROR",
                        T["DUPLICATE_OCCASION_IN_GROUP"].format(
                            group=group,
                            occasion=occ,
                            path=grade_config["__PATH__"]
                        )
                    )
                    continue
                ogd[group] = odata
    return occasions


def get_group_data(occasion: str, class_group: str):
    """Get configuration information pertaining to the grade table
    for the given group and "occasion".
    """
    try:
        return get_occasions_groups()[occasion][class_group]
    except KeyError:
        raise Bug(
            f'No grades config info for group "{class_group}",'
            f' "occasion" = {occasion}'
            f' in\n  {GetGradeConfig()["__PATH__"]}'
        )


class SubjectColumns(list):
    """A custom representation of the column data (subjects, etc.).
    It is a list, but with a look-up function ("get") for sid keys.
    Only indexing and the methods below are supported, using others
    might well make a mess ...
    """
    def __init__(self):
        super().__init__()
        self.__map = {}

    def append(self, subject_data):
        self.__map[subject_data["SID"]] = len(self)
        super().append(subject_data)

    def get(self, sid):
        return self[self.__map[sid]]

    def column(self, sid):
        return self.__map[sid]


class PupilRows(list):
    """A custom representation of the row data (pupils).
    It is a list, but with a look-up function ("get") for pid keys.
    Only indexing and the methods below are supported, using others
    might well make a mess ...
    """
    def __init__(self):
        super().__init__()
        self.__map = {}

    def append(self, pupil_data, grade_map):
        self.__map[pupil_data["PID"]] = len(self)
        super().append((pupil_data, grade_map))

    def get(self, pid):
        return self[self.__map[pid]]

    def column(self, pid):
        return self.__map[pid]

    def sort(self):
        l2 = sorted(self, key=lambda x: x[0]["SORT_NAME"])
        self.clear()
        self.__map.clear()
        for p, g in l2:
            self.append(p, g)


def grade_table_info(occasion: str, class_group: str, instance: str = ""):
    """Get subject, pupil and group report-information for the given
    parameters.
    """
    subjects, pupils = get_pupil_grade_matrix(class_group, text_reports=False)
    group_data = get_group_data(occasion, class_group)
    klass, group = class_group_split(class_group)
    ### Complete the columns list, including "normal" subjects, "composite"
    ### subjects, calculated fields and additional input fields.
    extra_fields = group_data.get("EXTRA_FIELDS") or []
    subject_list = SubjectColumns()
    column_lists = {
        "SUBJECT": subject_list,
        "COMPOSITE": SubjectColumns(),
        "CALCULATE": SubjectColumns(),
        "INPUT": SubjectColumns(),
    }
    for sdata in sorted(subjects.values()):
        sid = sdata[1]
        sname = sdata[2]
        zgroup = sdata[3]
        # sdata[4] is the text-report custom settings, which are
        # not relevant here.
        value = {
            "SID": sid,
            "NAME": sname,
            "GROUP": zgroup,
        }
        subject_list.append(value)
    result = {
        "OCCASION": occasion,
        "CLASS_GROUP": class_group,
        "INSTANCE": instance,
        "COLUMNS": column_lists,
    }

    for odata in extra_fields:
        otype = odata["TYPE"]
        osid = odata["SID"]
        ## Collect "components"
        component_list = []
        cmplist = odata.get("COMPONENTS")
        if cmplist:
            if isinstance(cmplist, list):
                for cmpsid in odata["COMPONENTS"]:
                    try:
                        cmpdata = subject_list.get(cmpsid)
                    except KeyError:
                        # This potential component sid is not used
                        continue
                    if "COMPOSITE" in cmpdata:
                        REPORT(
                            "ERROR",
                            T["COMPONENT_OF_COMPOSITE"].format(
                                path=GetGradeConfig()["__PATH__"],
                                group=class_group,
                                occasion=occasion,
                                sid=osid,
                                name=odata["NAME"],
                                csid=cmpsid,
                                cname=cmpdata["NAME"]
                            )
                        )
                    else:
                        # Include this component
                        component_list.append(cmpsid)
            else:
                REPORT(
                    "ERROR",
                    T["COMPONENTS_NOT_LIST"].format(
                        path=GetGradeConfig()["__PATH__"],
                        group=class_group,
                        occasion=occasion,
                        sid=osid,
                        name=odata["NAME"],
                    )
                )
                continue

        if otype == "COMPOSITE":
            if not component_list:
                REPORT(
                    "WARNING",
                    T["COMPOSITE_NO_COMPONENTS"].format(
                        path=GetGradeConfig()["__PATH__"],
                        group=class_group,
                        occasion=occasion,
                        sid=osid,
                        name=odata["NAME"]
                    )
                )
                continue # Don't include this composite subject
            for cmpsid in component_list:
                subject_list.get(cmpsid)["COMPOSITE"] = osid
            column_lists["COMPOSITE"].append(
                {
                    "SID": osid,
                    "NAME": odata["NAME"],
                    "FUNCTION": odata["FUNCTION"],
                    "GROUP": odata["GROUP"],
                    "PARAMETERS": {
                        "COMPONENTS": component_list
                    }
                }
            )
            continue

        if otype == "CALCULATE":
            if not component_list:
                # Collect all non-component subjects
                for item in subject_list:
                    if "COMPOSITE" not in item:
                        component_list.append(item["SID"])
                for item in column_lists["COMPOSITE"]:
                    component_list.append(item["SID"])
                if not component_list:
                    REPORT(
                        "WARNING",
                        T["CALCULATE_NO_COMPONENTS"].format(
                            path=GetGradeConfig()["__PATH__"],
                            group=class_group,
                            occasion=occasion,
                            sid=osid,
                            name=odata["NAME"]
                        )
                    )
                    continue # don't include this calculated field
            parms = {"COMPONENTS": component_list}
            try:
                parms.update(odata["PARAMETERS"])
            except KeyError:
                pass
            column_lists["CALCULATE"].append(
                {
                    "SID": osid,
                    "NAME": odata["NAME"],
                    "FUNCTION": odata["FUNCTION"],
                    "PARAMETERS": parms
                }
            )
            continue

        if otype == "INPUT":
            column_lists["INPUT"].append(
                {
                    "SID": osid,
                    "NAME": odata["NAME"],
                    "METHOD": odata["METHOD"],
                    "PARAMETERS": odata.get("PARAMETERS") or {}
                }
            )
            continue

        REPORT(
            "ERROR",
            T["INVALID_EXTRA_FIELD"].format(
                path=GetGradeConfig()["__PATH__"],
                group=class_group,
                occasion=occasion,
                sid=osid,
                name=odata["NAME"],
            )
        )

    result["GRADE_VALUES"] = group_data["GRADES"]
    result["GRADE_ENTRY"] = group_data.get("GRADE_ENTRY", "")
    result["SYMBOLS"] = group_data.get("SYMBOLS") or {}
    pupil_map = {}  # ordered dict!
    result["PUPILS"] = pupil_map
    for pdata, p_grade_tids in pupils:
        pupil_map[pdata["PID"]] = (pdata, p_grade_tids)
    return result


def FullGradeTable(occasion, class_group, instance):
    """Return full pupil and grade information – including calculated
    field values – for the given parameters.
    This may cause changes to the database, so that its contents
    correspond to the returned data.
    Pupils with no grade data will not be added to the database.
    """
    table = pupil_subject_grade_info(occasion, class_group, instance)
    prepare_pupil_list(table)
    return table


def pupil_subject_grade_info(occasion, class_group, instance):
    """Collate basic data for the report instance:
        configuration data for the subjects,
        pupil data list,
        stored grade info
    """
    ### Get config info, including pupil list ({key: value/data})
    table_info = grade_table_info(occasion, class_group, instance)
    ### Get database records for pupils and grades:
    ###     {pid: (pdata, grade-map), ... }
    ### Note that CLASS and LEVEL fields are taken from the database
    ### GRADES record.
    table_info["STORED_GRADES"] = {
        pdata["PID"]: (pdata, grademap)
        for pdata, grademap in read_stored_grades(
            occasion, class_group, instance
        )
    }
    ### Get general info from database concerning stored grades
    infolist = db_read_table(
        "GRADES_INFO",
        ["DATE_ISSUE", "DATE_GRADES", "MODIFIED"],
        CLASS_GROUP=class_group,
        OCCASION=occasion,
        INSTANCE=instance
    )[1]
    if infolist:
        if len(infolist) > 1:
            # This should not be possible
            raise Bug(
                f"Multiple entries in GRADES_INFO for {class_group}"
                f" / {occasion} / {instance}"
            )
        DATE_ISSUE, DATE_GRADES, MODIFIED = infolist[0]
    else:
        # No entry in database, add a new one using last day of school
        # year for initial date values – to ensure that the data will
        # remain "open".
        DATE_ISSUE = Dates.lastday(SCHOOLYEAR)
        DATE_GRADES = DATE_ISSUE
        MODIFIED = "–––––"
        db_new_row("GRADES_INFO",
            CLASS_GROUP=class_group,
            OCCASION=occasion,
            INSTANCE=instance,
            DATE_ISSUE=DATE_ISSUE,
            DATE_GRADES=DATE_GRADES
        )
    table_info["DATE_ISSUE"] = DATE_ISSUE
    table_info["DATE_GRADES"] = DATE_GRADES
    table_info["MODIFIED"] = MODIFIED
    return table_info


def read_stored_grades(
    occasion: str,
    class_group: str,
    instance: str = ""
) -> list[tuple[dict, dict]]:
    """Return an ordered list containing personal info and grade info
    from the database for each pupil covered by the parameters.
    """
    fields = [
        # "OCCASION",
        # "CLASS_GROUP",
        # "INSTANCE",
        "PID",
        "LEVEL",  # The level might have changed, so this field is relevant
        "GRADE_MAP",
    ]
    flist, rlist = db_read_table(
        "GRADES",
        fields,
        OCCASION=occasion,
        CLASS_GROUP=class_group,
        INSTANCE=instance,
    )
    plist = []
    for row in rlist:
        pid = row[0]
        pdata = pupil_data(pid)  # this mapping is not cached => it is mutable
        # Save current volatile field values
        pdata["__CLASS__"] = pdata["CLASS"]
        pdata["__LEVEL__"] = pdata["LEVEL"]
        # Substitute these fields with data from the record
        pdata["CLASS"] = class_group_split(class_group)[0]
        pdata["LEVEL"] = row[1]
        # Get grade (etc.) info as mapping
        grade_map = read_pairs(row[2])
        plist.append((pdata, dict(grade_map)))
    return plist


def prepare_pupil_list(table_info):
    """Tweak the list of pupils taking the current date into account.
    If the grading date (DATE_GRADES) is before "today", only the pupils
    with grades stored in the database will be included – this is
    regarded as a "closed category" (report-set instance), the group data
    is assumed to have been correct at the grading date. For closed
    category data only inspection of the data or possibly minor tweaks
    are expected.
    The database grade entries do not include pupils' personal data, this
    must be taken from the standard (current) pupils table. It is
    assumed that this won't change in the course of a year, with one or
    two exceptions:
     - A pupil might leave (and so be absent from later lists, but the
       other data should still be there).
     - There might be fixes (which I assume should also be incorporated
       in older data, if relevant).
     - The LEVEL field might change (for old data keep the old version).
       To enable retention, this field is added to the grade mapping.
    Finally, the field values are recalculated and the database entries
    updated if there has been a change.
    """
    pdata_list = PupilRows()    # [(pdata, grades),  ... ]
    table_info["PUPIL_LIST"] = pdata_list
    class_group = table_info["CLASS_GROUP"]
    occasion = table_info["OCCASION"]
    instance = table_info["INSTANCE"]
    DATE_GRADES = table_info["DATE_GRADES"]
    if DATE_GRADES < Dates.today():
        # Closed category: include only pupils with stored grade entries,
        # i.e. assume the list of pupils is fixed at the grading date.
        for db_pdata, db_grademap in table_info["STORED_GRADES"].values():
            pname = pupil_name(db_pdata)
            if db_pdata["CLASS"] != db_pdata["__CLASS__"]:
                REPORT(
                    "WARNING",
                    T["CLASS_CHANGED"].format(
                        name=pname,
                        new_class=db_pdata["__CLASS__"]
                    )
                )
            if db_pdata["LEVEL"] != db_pdata["__LEVEL__"]:
                REPORT(
                    "WARNING",
                    T["LEVEL_CHANGED"].format(
                        name=pname,
                        db_level=db_pdata["LEVEL"],
                        new_level=db_pdata["__LEVEL__"]
                    )
                )
            # Update the grade map and add to pupil list
            complete_gradetable(table_info, db_pdata, db_grademap)

        if pdata_list:
            pdata_list.sort()
        else:
            REPORT("WARNING", T["NO_PUPIL_GRADES"].format(
                report_info=f"{class_group} / {occasion} / {instance}"
            ))

    else:
        # print("%grades_base: table open")
        # Category still open, use current pupil list, grades from database
        for pid, data in table_info.pop("PUPILS").items():
            pdata, sid_tids = data
            exit_date = pdata["DATE_EXIT"]
            if exit_date and DATE_GRADES > exit_date:
                continue    # pupil has left the school
            pname = pupil_name(pdata)
            try:
                db_pdata, db_grademap = table_info["STORED_GRADES"].pop(pid)
            except KeyError:
#TODO: Is this right???
                db_pdata = pdata
                db_grademap = {}
            else:
                if db_pdata["LEVEL"] != pdata["LEVEL"]:
                    REPORT(
                        "WARNING",
                        T["LEVEL_UPDATED"].format(
                            name=pname,
                            db_level=db_pdata["LEVEL"],
                            new_level=pdata["LEVEL"],
                        )
                    )
                    # Update db field
                    db_update_field("GRADES", "LEVEL", pdata["LEVEL"],
                        OCCASION=occasion,
                        CLASS_GROUP=class_group,
                        INSTANCE=instance,
                        PID=pid
                    )
            # Update the grade map and add to pupil list
            complete_gradetable(table_info, db_pdata, db_grademap, sid_tids)
        # Remove pupils from grade table if they are no longer in the group.
        # This must be done because otherwise they would be "reinstated"
        # as soon as the date-of-issue is past.
        for pid, data in table_info["STORED_GRADES"].items():
            REPORT(
                "WARNING",
                T["REMOVING_PUPIL_GRADES"].format(
                    name=pupil_name(data[0])
                )
            )
            db_delete_rows("GRADES",
                OCCASION=occasion,
                CLASS_GROUP=class_group,
                INSTANCE=instance,
                PID=pid
            )
    del(table_info["STORED_GRADES"])
    return table_info


def set_grade_update_time(table_info) -> str:
    """Set the modification date+time for a report instance.
    Call after changes to the grade information.
    """
    timestamp = Dates.timestamp()
    db_update_field("GRADES_INFO", "MODIFIED", timestamp,
        OCCASION=table_info["OCCASION"],
        CLASS_GROUP=table_info["CLASS_GROUP"],
        INSTANCE=table_info["INSTANCE"]
    )
    table_info["MODIFIED"] = timestamp
    return timestamp


def complete_grademap(column_lists, grades, name, p_grade_tids):
    """Ensure that the given grade data is "complete", according to
    the subjects list for the group and the subjects for which this
    pupil has a teacher (if this data is available).
    Entries in the <column_lists> with a FUNCTION field are not
    copied over, they do not belong to the stored data and will be
    calculated anew (later).
    """
    grade_map = {}
    for sdata in column_lists["SUBJECT"]:
        sid = sdata["SID"]
        # print("\n$$$$$$$$", sid, p_grade_tids, grades)
#TODO: Check validity?
        if p_grade_tids is None:
            # for "closed" data-sets
            try:
                grade_map[sid] = grades[sid]
            except KeyError:
                continue
        elif p_grade_tids.get(sid):
            grade_map[sid] = grades.get(sid) or ""
        else:
            try:
                g = grades[sid]
            except KeyError:
                continue
            if g:
#TODO: Warning – bodge!
                if sid.endswith(".x"):
                    grade_map[sid] = g
                else:
                    REPORT(
                        "WARNING",
                        T["GRADE_WITH_NO_TEACHER"].format(
                            sid=sid,
                            sname=sdata["NAME"],
                            grade=grades[sid],
                            pupil=name,
                        )
                    )
    for sdata in column_lists["INPUT"]:
        sid = sdata["SID"]
        try:
            grade_map[sid] = grades[sid]
        except KeyError:
            # Consider the value list for defaults, taking
            # the first entry
            try:
                values = sdata["VALUES"]
            except KeyError:
                grade_map[sid] = ""
            else:
                if values:
                    default = values[0]
                else:
                    default = ""
                # The value can be a single string or a pair
                if isinstance(default, list):
                    grade_map[sid] = default[0]
                else:
                    grade_map[sid] = default
    return grade_map


def complete_gradetable(table, db_pdata, db_grademap, p_grade_tids=None):
    """Process the raw grades from the database when the data for a
    pupil group is loaded. It ensures that all necessary "columns" and
    grades are present.
    Subsequent changes to the data (editing) will be handled by
    a separate function.
    """
    column_lists = table["COLUMNS"]
    grades = complete_grademap(
        column_lists,
        db_grademap,
        pupil_name(db_pdata),  # just for messages
        p_grade_tids
    )
    table["PUPIL_LIST"].append(db_pdata, grades)
    # It cannot be assumed that all the subjects have grades – some
    # will only appear after the calculations. Thus their grades will
    # not (necessarily) be in <grades>. The calculations would need
    # access to the raw grade from the database (<db_grademap>).
    calculate_grades(table, db_pdata["PID"], db_grademap)
    # The results are not used here.


def UpdatePupilGrades(table: dict, pid: str
) -> tuple[list[tuple[str, str]], Optional[str]]:
    """Recalculate table row.
    <table> is the full grade table.
    Return (changes, timestamp).
    The changes are to (existing) entries in the initial grade set,
    in the form [(sid, OLD value), ... ].
    """
    # print("§UPDATE", pid, grades := table["PUPIL_LIST"].get(pid)[1])
    return calculate_grades(table, pid, None)


def calculate_grades(
    table: dict,
    pid: str,
    old_grades:Optional[dict]
) -> tuple[list[tuple[str, str]], Optional[str]]:
    ## Save initial grade map so that changes can be determined
    grades = table["PUPIL_LIST"].get(pid)[1]
    grades0 = list(grades.items())
    ## Perform calculations
    column_lists = table["COLUMNS"]
    for slist in ("COMPOSITE", "CALCULATE"):
        subjects = column_lists[slist]
        for sdata in subjects:
            fn = sdata["FUNCTION"]
            # The function modifies <grades>
            newsubjects = GradeFunction(fn, sdata, grades, old_grades)
            # Any column additions?
            if newsubjects:
                ctset = set()
                for ctype, cdata in newsubjects:
                    cl = column_lists[ctype]
                    cl.append(cdata)
                    ctset.add(ctype)
                for ctype in ctset:
                    if ctype in ("SUBJECT", "COMPOSITE"):
                        # Re-sort the column list
                        column_lists[ctype].sort(
                            key=lambda k: (k["GROUP"], k["NAME"])
                        )
    ## Collect changes to (existing) entries in the initial grade set
    changes0 = []
    for sid, g0 in grades0:
        if grades.get(sid) != g0:
            changes0.append((sid, g0))
    ## Save grades if one or more of the base set (subjects and inputs)
    ## differs from the stored values. Empty values are not saved (the
    ## sid is simply not included in the saved string).
    ## <FullGradeTable> (called before this function) adds missing
    ## subject entries.
    change = old_grades is None
    base_grades = {}
    for slist in ("SUBJECT", "INPUT"):
        subjects = column_lists[slist]
        for sdata in subjects:
            sid = sdata["SID"]
            g1 = grades.get(sid)
            if old_grades is None:
                if g1:
                    base_grades[sid] = g1
            else:
                g0 = old_grades.get(sid)
                if g1:
                    base_grades[sid] = g1
                    if g1 != g0:
                        change = True
                elif g0:
                    change = True

# Note that previously empty "INPUT" items will have acquired a default
# value ... ideally a change should only be registered when the new
# value differs from this, but this may be impractical ...

    if change:
        # Rewrite database entry, getting the timestamp
        t = update_grade_entry(table, pid, base_grades)
    else:
        t = ""
    return (changes0, t)


def update_grade_entry(table: dict, pid: str, grades: dict[str, str]
) -> str:
    """Update the database GRADES entry of the pupil with id <pid>
    for the occasion/instance of the <table> parameter.
    If there is no existing entry, a new one will be created.
    Return the new timestamp.
    """
    gstring = write_pairs_dict(grades)
    OCCASION = table["OCCASION"]
    CLASS_GROUP = table["CLASS_GROUP"]
    INSTANCE = table["INSTANCE"]
    if not db_update_field("GRADES",
        "GRADE_MAP", gstring,
        OCCASION=OCCASION,
        CLASS_GROUP=CLASS_GROUP,
        INSTANCE=INSTANCE,
        PID=pid
    ):
        db_new_row("GRADES",
            OCCASION=OCCASION,
            CLASS_GROUP=CLASS_GROUP,
            INSTANCE=INSTANCE,
            PID=pid,
            LEVEL=pupil_data(pid)["LEVEL"],
            GRADE_MAP=gstring
        )
    timestamp = set_grade_update_time(table)
    return timestamp


#TODO: Needs updating? If it is still used ...
def FullGradeTableUpdate(table, pupil_grades):
    """Update the grades in a report category (a <FullGradeTable>) from
    an external source.
    The parameter <pupil_grades> should be a mapping:
        {pid: {sid: grade, ...}, ...}
        with special entries:
            "__INFO__": general info
        and
            "__PUPILS__": {pid: {"PUPIL": name, "LEVEL": level}, ... }
    This structure can be obtained by reading a table using <LoadFromFile>.

    It is possible that the list of pupils doesn't correspond to that in
    the database (though that shouldn't be the normal case!). Warnings
    will be issued for such mismatches.
#TODO?
    There is also a warning if there is an attempt to place a grade in
    a "forbidden" (NO_GRADE) slot, or if trying to overwrite a grade
    with a NO_GRADE.
    If the LEVEL doesn't match, issue a warning but use the value from
    the database, not the new one.

    This function should not be used to update a "closed category", it
    might not work.
    """
    assert False, "TODO: needs updating"
    pinfo = pupil_grades.pop("__PUPILS__")
#    info = pupil_grades.pop("__INFO__")
    for pdata, grades in table["PUPIL_LIST"]:
        pid = pdata["PID"]
        try:
            new_grades = pupil_grades.pop(pid)
        except KeyError:
            REPORT(
                "WARNING",
                T["NOT_IN_TABLE"].format(
                    name=pupil_name(pdata)
                )
            )
            continue
        table_level = pinfo[pid]["LEVEL"]
        if table_level != pdata["LEVEL"]:
            REPORT(
                "WARNING",
                T["LEVEL_MISMATCH"].format(
                    name=pupil_name(pdata),
                    table_level=table_level
                )
            )

        # print("\n§§§§§", pupil_name(pdata), new_grades)
        bad_sids = set()
        grades_x = {}    # updated grades
        for s, g in new_grades.items():
            if not g:
               continue     # ignore empty fields
            try:
                g0 = grades[s]
            except KeyError:
                if s not in bad_sids: # Just report once
                    bad_sids.add(s)
                    REPORT("WARNING", T["UNKNOWN_SID"].format(sid=s))
                continue
            if g == g0:
                continue
            if g == NO_GRADE and not g0:
                REPORT(
                    "ERROR",
                    T["GRADE_STOMPED"].format(
                        name=pupil_name(pdata),
                        sid=s,
                        grade=g0
                    )
                )
                continue
            elif g0 == NO_GRADE and not g:
                REPORT(
                    "ERROR",
                    T["NO_GRADE_VALUE"].format(
                        name=pupil_name(pdata),
                        sid=s,
                        grade=g0
                    )
                )
                continue
            grades_x[s] = g
        if grades_x:
            # print("§§§§§§§ Updating", pupil_name(pdata))
            grades.update(grades_x)
            UpdatePupilGrades(table, pid)
    ### Excess pupils:
    for pid in pupil_grades:
        REPORT(
            "WARNING",
            T["PUPIL_NOT_IN_GROUP"].format(name=pinfo[pid]["PUPIL"])
        )


def UpdateTableInfo(table, field, value) -> str:
    """Update a single field in the current (for <table>) GRADES_INFO
    entry.
    Return the new "modified" timestamp.
    """
    db_update_field("GRADES_INFO", field, value,
        OCCASION=table["OCCASION"],
        CLASS_GROUP=table["CLASS_GROUP"],
        INSTANCE=table["INSTANCE"]
    )
    return set_grade_update_time(table)


def MakeGradeTable(table:dict, clear:bool=False) -> bytes:
    """Build a basic pupil/subject table for grade input using a
    template appropriate for the given group.
    """
    grade_info = GetGradeConfig()

    ### Get template file
    try:
        gefile = table["GRADE_ENTRY"]
    except KeyError:
        REPORT(
            "ERROR",
            T["NO_GRADE_ENTRY_FILE"].format(
                path=grade_info["__PATH__"],
                OCCASION=table["OCCASION"],
                CLASS_GROUP=table["CLASS_GROUP"],
            )
        )
        return b''
    template_path = RESOURCEPATH("templates/" + gefile)
    gtable = KlassMatrix(template_path)

    ### Set title line
    gtable.setTitle(
        T["TITLE"].format(
            time=datetime.datetime.now().isoformat(sep=" ", timespec="minutes")
        )
    )

    ### Gather general info
    DATE_ISSUE = table["DATE_ISSUE"]
    if not DATE_ISSUE:
        DATE_ISSUE = Dates.today()
    DATE_GRADES = table["DATE_GRADES"]
    if not DATE_GRADES:
        DATE_GRADES = DATE_ISSUE
    info_item: dict
    info_transl: dict[str, str] = dict(grade_info["INFO_FIELDS"])
    date_format = CONFIG["DATEFORMAT"]
    info: dict[str, str] = {
        info_transl["SCHOOLYEAR"]: SCHOOLYEAR,
        info_transl["CLASS_GROUP"]: table["CLASS_GROUP"],
        info_transl["OCCASION"]: table["OCCASION"],
        info_transl["INSTANCE"]: table["INSTANCE"],
        info_transl["DATE_GRADES"]: Dates.print_date(DATE_GRADES, date_format),
        info_transl["DATE_ISSUE"]: Dates.print_date(DATE_ISSUE, date_format),
    }
    gtable.setInfo(info)

    ### Go through the template columns and check if they are needed:
    rowix: list[int] = gtable.header_rowindex  # indexes of header rows
    if len(rowix) != 2:
        REPORT(
            "ERROR",
            T["TEMPLATE_HEADER_WRONG"].format(path=template_path)
        )
        return b''
    sidcol: list[tuple[str, int]] = []
    sid: str
    sdata: dict
    for sdata in table["COLUMNS"]["SUBJECT"]:
        # Add subject
        sid = sdata["SID"]
        col: int = gtable.nextcol()
        sidcol.append((sid, col))
        gtable.write(rowix[0], col, sid)
        gtable.write(rowix[1], col, sdata["NAME"])
    # Enforce minimum number of columns
    while col < 18:
        col = gtable.nextcol()
        gtable.write(rowix[0], col, "")
    # Delete excess columns
    gtable.delEndCols(col + 1)
    ### Add pupils and grades
    for pdata, pgrades in table["PUPIL_LIST"]:
        row = gtable.nextrow()
        gtable.write(row, 0, pdata["PID"])
        gtable.write(row, 1, pupil_name(pdata))
        gtable.write(row, 2, pdata["LEVEL"])
        for sid, col in sidcol:
            try:
                g = pgrades[sid]
            except KeyError:
                gtable.write(row, col, NO_GRADE, protect=True)
            else:
                gtable.write(row, col, g)
    # Delete excess rows
    row = gtable.nextrow()
    gtable.delEndRows(row)

    ### Save file
    gtable.protectSheet()
    return gtable.save_bytes()


def LoadFromFile(
    filepath: str,
    OCCASION: str,
    CLASS_GROUP: str,
    INSTANCE: str = "",
    **kargs # allows passing additional (unused) parameters
):
    """Read a grade table from the given file path. The file information
    is checked to ensure that it corresponds to the desired report
    category.
    """
    data = read_grade_table_file(filepath)
    # -> dict[str, dict[str, str]]
    info = data["__INFO__"]
    val = info.get("SCHOOLYEAR")
    if val != SCHOOLYEAR:
        REPORT("ERROR", T["SCHOOLYEAR_MISMATCH"].format(val=val))
        return None
    val = info.get("OCCASION")
    if val != OCCASION:
        REPORT("ERROR", T["OCCASION_MISMATCH"].format(val=val))
        return None
    val = info.get("CLASS_GROUP")
    if val != CLASS_GROUP:
        REPORT("ERROR", T["CLASS_GROUP_MISMATCH"].format(val=val))
        return None
    val = info.get("INSTANCE")
    if val != INSTANCE:
        REPORT("ERROR", T["INSTANCE_MISMATCH"].format(val=val))
        return None
    return data


def read_grade_table_file(
    filepath: str,
) -> dict[str, dict[str, str]]:
    """Read the header info and pupils' grades from the given grade
    table (file).
    <read_DataTable> in the "spreadsheet" module is used as backend, so
    .ods, .xlsx and .tsv formats are possible. The filename may be
    passed without extension – <Spreadsheet> then looks for a file with
    a suitable extension.
    Return mapping for pupil-grades. Include header info as special
    entry.
    """
    grade_config = GetGradeConfig()
    header_map = grade_config["HEADERS"]
    info_map = {t: f for f, t in grade_config["INFO_FIELDS"]}
    datatable = read_DataTable(filepath)
    info = {(info_map.get(k) or k): v for k, v in datatable["__INFO__"].items()}
    ### Get the rows as mappings
    # fields = datatable["__FIELDS__"]
    pinfo_map = {}
    gdata: dict[str, dict[str, str]] = {
        "__INFO__": info,
        "__PUPILS__": pinfo_map,
    }
    group_data = get_group_data(info["OCCASION"], info["CLASS_GROUP"])
    valid_grades = get_valid_grades(group_data["GRADES"])
    for pdata in datatable["__ROWS__"]:
        pinfo = {h: pdata.pop(t) for h, t in header_map}
        pid: str = pinfo.pop("PID")
        if pid == "$":
            continue
        pinfo_map[pid] = pinfo
        gdata[pid] = pdata
        # Check validity of grades
        for k, v in pdata.items():
            if v and v not in valid_grades:
                print("§valid_grades:", valid_grades)
                REPORT(
                    "ERROR",
                    T["INVALID_GRADE"].format(
                        filepath=info["__FILEPATH__"],
                        pupil=pinfo["PUPIL"],
                        sid=k,
                        grade=v,
                    ),
                )
                pdata[k] = ""
    return gdata


def get_valid_grades(value_table) -> dict[str,str]:
    """Make a mapping of valid grades to their print values from the
    configuration table (in GRADE_CONFIG).
    """
    gmap = {}
    for row in value_table:
        text = row[1]
        for val in row[0]:
            gmap[val] = text or val
    return gmap


#TODO ... old code, GradeTableError is undefined
def collate_grade_tables(
    files: list[str],
    occasion: str,
    group: str,
) -> dict[str, dict[str, str]]:
    """Use <read_grade_table_file> to collect the grades from a set of grade
    tables – passed as <files>.
    Return the collated grades: {pid: {sid: grade}}.
    Only grades that have actually been given (i.e. no empty grades or
    grades for unchosen or unavailable subject) will be included.
    If a grade for a pupil/subject pair is given in multiple input tables,
    an exception will be raised if the grades are different.
    """
    grades: dict[str, dict[str, str]] = {}
    # For error tracing, retain file containing first definition of a grade.
    fmap: dict[tuple[str, str], str] = {}  # {(pid, sid): filepath}
    for filepath in files:
        table = read_grade_table_file(filepath)
        info = table.pop("__INFO__")
        if info["SCHOOLYEAR"] != SCHOOLYEAR:
            raise GradeTableError(
                T["TABLE_YEAR_MISMATCH"].format(
                    year=SCHOOLYEAR, filepath=info["__FILEPATH__"]
                )
            )
        if info["CLASS_GROUP"] != group:
            raise GradeTableError(
                T["TABLE_CLASS_MISMATCH"].format(
                    group=group, path=info["__FILEPATH__"]
                )
            )
        if info["OCCASION"] != occasion:
            raise GradeTableError(
                T["TABLE_TERM_MISMATCH"].format(
                    term=occasion, path=info["__FILEPATH__"]
                )
            )
        for pid, smap in table.items():
            try:
                smap0 = grades[pid]
            except KeyError:
                smap0 = {}
                grades[pid] = smap0
            for s, g in smap.items():
                if g:
                    if (not g) or g == NO_GRADE:
                        continue
                    g0 = smap0.get(s)
                    if g0:
                        if g0 != g:
                            raise GradeTableError(
                                T["GRADE_CONFLICT"].format(
                                    pid=pid,
                                    sid=s,
                                    path1=fmap[(pid, s)],
                                    path2=filepath,
                                )
                            )
                    else:
                        smap0[s] = g
                        fmap[(pid, s)] = filepath
    return grades


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.db_access import open_database

    open_database()

    print("\n*** occasions_groups:")
    for k, v in get_occasions_groups().items():
        print("\n  +++", k)
        for g, data in v.items():
            print("\b   --------", g)
            print(data)

    print("\n *** group data: class 13, Abitur")
    print(get_group_data("Abitur", "13"))


    # gtinfo = grade_table_info("1. Halbjahr", "12G.R")
    gtinfo = grade_table_info("Abitur", "13")
    # gtinfo = grade_table_info("2. Halbjahr", "12G.R")
#    print("\n*** SUBJECTS")
#    for val in gtinfo["SUBJECTS"]:
#        print("    ---", val)
    print("\n*** COLUMNS")
#! was just a single list ...
    for item in gtinfo.pop("COLUMNS"):
        print("\n    ---", item)
    print("\n*** GRADE_VALUES", gtinfo.pop("GRADE_VALUES"))
    print("\n*** PUPILS")
    for pid, pinfo in gtinfo.pop("PUPILS").items():
        pdata, p_grade_tids = pinfo
        print(f"\n +++ {pdata}")
        print(" .........", p_grade_tids)

    print("\n\n REMAINDER:\n", gtinfo)

    print("\n\n Full Grade Table:")
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # fgtable = FullGradeTable("Abitur", "13", "")
    # fgtable = FullGradeTable("1. Halbjahr", "12G.R", "")
    # fgtable = FullGradeTable("1. Halbjahr", "13", "")
    fgtable = FullGradeTable("2. Halbjahr", "12G.R", "")

    for k, v in fgtable.items():
        print("\n =======", k, "\n", v)

#TODO--
    quit(0)

    ipath = OPEN_FILE(
        filetype="Tabelle (*.xlsx *.ods *.tsv)",
        start="",
        title=f"Input Grades for {fgtable['CLASS_GROUP']} / {fgtable['OCCASION']}"
    )
    if ipath:
        print("\n§§§", ipath)
        itable = LoadFromFile(ipath, **fgtable)
        if itable:
            #for k, v in itable.items():
            #    print("\n $$$", k, v)
            FullGradeTableUpdate(fgtable, itable)

    for __cg in ("13", "11G", "12G.G", "12G.R"):
        fgtable = FullGradeTable("1. Halbjahr", __cg, "")
        tbytes = MakeGradeTable(fgtable, True)
        tpath = DATAPATH(f"testing/tmp/GradeInput-{__cg}.xlsx")
        tdir = os.path.dirname(tpath)
        if not os.path.isdir(tdir):
            os.makedirs(tdir)
        with open(tpath, "wb") as _fh:
            _fh.write(tbytes)
        print(f"\nWROTE GRADE TABLE TO {tpath}\n")

    print("\n *************************************************\n")

    quit(0)

    _o = "1. Halbjahr"
    _cg = "13"
    _i = ""
    path = OPEN_FILE("Tabelle (*.xlsx *.ods *.tsv)")
    if path:
        pid2grades = load_from_file(
            filepath=path,
            occasion=_o,
            class_group=_cg,
            instance=_i,
        )
        # Merge in pupil info
        for pid, pinfo in pid2grades["__PUPILS__"].items():
            pid2grades[pid].update(pinfo)
        print("\n\n ************ pid2grades **********************\n", pid2grades)
        print("\n\n *********************************\n")
        gt = full_grade_table(_o, _cg, _i, pid2grades)

    for __cg in ("13", "11G", "12G.G", "12G.R"):
        #    for __cg in ("11G", "12G.G", "12G.R"):
        tbytes = make_grade_table("1. Halbjahr", __cg)
        tpath = DATAPATH(f"testing/tmp/GradeInput-{__cg}.xlsx")
        tdir = os.path.dirname(tpath)
        if not os.path.isdir(tdir):
            os.makedirs(tdir)
        with open(tpath, "wb") as _fh:
            _fh.write(tbytes)
        print(f"\nWROTE GRADE TABLE TO {tpath}\n")

    print("\n *************************************************\n")

    gdata = read_grade_table_file(tpath)
    for pid, pdata in gdata.items():
        print(f"\n --- {pid}:", pdata)

    print("\nCOLLATING ...")
    from glob import glob

    gtable = collate_grade_tables(
        glob(os.path.join(tdir, "test?.xlsx")), "1. Halbjahr", "11G"
    )
    for p, pdata in gtable.items():
        print("\n ***", p, pdata)

    print("\n *************************************************\n")

    gtinfo = grade_table_info("2. Halbjahr", "12G.R")
    print("\n*** SUBJECTS")
    for val in gtinfo["SUBJECTS"]:
        print("    ---", val)
    print("\n*** COMPOSITE-COMPONENTS")
    for val in gtinfo["COMPONENTS"]:
        print("    ---", val)
    print("\n*** COMPOSITES")
    for val in gtinfo["COMPOSITES"]:
        print("    ---", val)
    print("\n*** EXTRA COLUMNS")
    for val in gtinfo["EXTRAS"]:
        print("    ---", val)
    print("\n*** GRADES", gtinfo["GRADES"])
    print("\n*** PUPILS")
    for pid, pinfo in gtinfo["PUPILS"].items():
        pdata, p_grade_tids = pinfo
        print(f"\n +++ {pdata}")
        print(" .........", p_grade_tids)

    print("\n*** STORED GRADES")
    stored_grades = read_stored_grades("1. Halbjahr", "12G.R")

    print("\n******************************************************")

    #grade_table = full_grade_table("1. Halbjahr", "12G.R", "").items()
    #grade_table = full_grade_table("1. Halbjahr", "13", "").items()
    #grade_table = full_grade_table("Kursnoten", "13", "Klausur 1").items()
    grade_table = full_grade_table("2. Halbjahr", "12G.R", "").items()

    print("\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

    for k, v in grade_table:
        print("\n =======", k, "\n", v)

    print("\n&&&&&&&&&&&&&&&&&", get_group_data("1. Halbjahr", "13"))
