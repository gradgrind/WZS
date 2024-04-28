"""
timetable/w365/w365base.py - last updated 2024-04-28

Basic functions for:
    Reading a Waldorf365 file.
    Saving to a WZ database.


=+LICENCE=================================
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
=-LICENCE=================================
"""

### +++++

import os

from core.db_access import Database, to_json

LIST_SEP = "#"  # use "," for xml input

def convert_date(date):
    #return date     # the dates are correct in the xml file
    d, m, y = (x.strip() for x in date.split("."))
    return f"{y}-{m}-{d}"

# Item types
_Course = "Course"
_Day = "Day"
_Group = "Group"
_Lesson = "Lesson"
_Period = "TimedObject"     # lesson slot
_Room = "Room"
_Schedule = "Schedule"
_Student = "Student"
_Subject = "Subject"
_Teacher = "Teacher"
_Year = "Grade"
_YearDiv = "GradePartiton"  # sic!

# Fields: Prefix with "@" for xml input via xmltodict
_Absences = "Absences"
_capacity = "capacity"
_Categories = "Categories"
_ContainerId = "ContainerId"
_CountryCode = "CountryCode"
_DateOfBirth = "DateOfBirth"
_day = "day"
_DoubleLessonMode = "DoubleLessonMode"
_EditedScenario = "EditedScenario"
_Email = "Email"
_End = "End"
_EpochFactor = "EpochFactor"
_EpochPlan = "EpochPlan"
_EpochPlanYear = "EpochPlanGrade"
_EpochWeeks = "EpochWeeks"
_FirstAfternoonHour = "FirstAfternoonHour"
_Firstname = "Firstname"
#TODO: Needs mods to Waldorf 365 to support both forms
_Firstnames = "Firstname"
_First_Name = "Firstname"

_Fixed = "Fixed"
_ForceFirstHour = "ForceFirstHour"
_Gender = "Gender"
_Groups = "Groups"
_HandWorkload = "HandWorkload"
_Home = "City"
_Hour = "Hour"
_hour = "hour"
_HoursPerWeek = "HoursPerWeek"
_Id = "Id"
_Lessons = "Lessons"
_Letter = "Letter"
_Level = "Level"
_ListPosition = "ListPosition"
#_LocalRooms = "LocalRooms"
_MaxDays = "MaxDays"
_MaxLessonsPerDay = "MaxLessonsPerDay"
_MaxGapsPerDay = "MaxWindowsPerDay"
_MiddayBreak = "MiddayBreak"
_MinLessonsPerDay = "MinLessonsPerDay"
_Name = "Name"
_NumberOfAfterNoonDays = "NumberOfAfterNoonDays"
_PhoneNumber = "PhoneNumber"
_PlaceOfBirth = "CityOfBirth"
_Postcode = "PLZ"
_PreferredRooms = "PreferredRooms"
_RoomGroup = "RoomGroup"
_Rooms = "Rooms"
_SchoolName = "SchoolName"
_Shortcut = "Shortcut"
_Start = "Start"
_StateCode = "StateCode"
_Street = "Street"
_StudentId = "ExtraId"
_Students = "Students"
_Subjects = "Subjects"
_Teachers = "Teachers"
_YearDivs = "GradePartitions"

### -----


# Dates: In the Waldorf365 data dumps, "DateOfBirth" fields are not
# ISO dates, but like "22. 01. 2015" (how reliable is this?).

# I may want to reimplement the "Database" class for the way the
# database is used in this module.

class W365_DB:
    """Apart from collecting the data from a Waldorf365 dump file, an
    in-memory database is created, containing the basic information in
    a Waldorf365-independent form. If desired this can be saved to an
    sqlite database file (see method "save").
    """
    def __init__(self, filedata):
        self.db = Database(":memory:")
        schoolstate = filedata["$$SCHOOLSTATE"]
        self.config = {
            "SCHOOL": schoolstate[_SchoolName],
            "STATE": schoolstate[_StateCode],
            "COUNTRY": schoolstate[_CountryCode],
        }
        self._scenarios = filedata["$$SCENARIOS"]
        self.scenario = filedata["$$SCENARIO"]
        self.idmap = filedata["$$IDMAP"]
        self.tables = {}
        self.id2key = {}
        self.key2node = {}

    def save(self, dbpath):
        try:
            os.remove(dbpath)
        except FileNotFoundError:
            pass
        self.db.query(f"vacuum main into '{dbpath}'")

    def add_nodes(self, table, w365id_nodes):
        values = [(table, to_json(n)) for _, n in w365id_nodes]
        keys = self.db.insertnodes(values)
        assert len(keys) == len(w365id_nodes)
        try:
            tlist = self.tables[table]
        except KeyError:
            tlist = []
            self.tables[table]= tlist
        for i, k in enumerate(keys):
            _id, n = w365id_nodes[i]
            if _id:
                self.id2key[_id] = k
            self.key2node[k] = n
            n["$KEY"] = k
            tlist.append(n)

    def config2db(self):
        self.db.insert(
            "NODES",
            ["DB_TABLE", "DATA"],
            ["__CONFIG__", to_json(self.config)]
        )

    def set_subject_activities(self, subject_activities):
        self.subject_activities = subject_activities

    def set_full_atomic_groups(self, atomic_groups):
        self.full_atomic_groups = atomic_groups


def read_active_scenario(w365path):
    filedata = read_w365(w365path)
    scenario_id = filedata['$$SCHOOLSTATE']['ActiveScenario']
    filedata['$$SCENARIO'] = filedata['$$SCENARIOS'][scenario_id]
    return filedata


def read_w365(filepath: str):
    """Read the format used in Waldorf365 data dumps ("Save"/"Load" actions).
    """
# To convert colours – which are here negative integers – to 6-digit
# hex (#RRGGBB): f"#{(0x1000000+colour):06X}"
    with open(filepath, "r", encoding = "utf-8") as fh:
        intext = fh.read()
    item = None
    _scenarios = []
    schoolstate = None
    items = []
    for line in intext.splitlines():
        if not line:
            item = None
            continue
        if line[0] == "*":
            if line == "*":
                break
            item = {}
            if line == "*Scenario":
                _scenarios.append(item)
                continue
            if line == "*SchoolState":
                schoolstate = item
                continue
            item["$$SECTION"] = line[1:]
            items.append(item)
            continue
        if item is None:
            continue
        k, v = line.split("=", 1)
        item[k] = v
    scenarios = {
        item[_Id]: {"$$SCENARIO": item}
        for item in _scenarios
    }
    idmap = {}
    w365 = {
        "$$SCHOOLSTATE": schoolstate,
        "$$SCENARIOS": scenarios,
        "$$IDMAP": idmap,
    }
# I might want to retain just the "chosen" scenario?
    for item in items:
        idmap[item[_Id]] = item
        sect = item.pop("$$SECTION")
        scen = scenarios[item[_ContainerId]]
        try:
            scen[sect].append(item)
        except KeyError:
            scen[sect] = [item]
    for contid, scen in scenarios.items():
        for sect, itemlist in scen.items():
            if sect[0] == "$":
                continue
            itemlist.sort(key = lambda x: x[_ListPosition])
    return w365


def absences(idmap, node):
    a0 = node.get(_Absences)
    absences = {}
    if a0:
        alist = []
        for w365id in a0.split(LIST_SEP):
            a = idmap[w365id]
            alist.append((int(a[_day]), int(a[_hour])))
        alist.sort()
        for day, hour in alist:
            try:
                absences[day].append(hour)
            except KeyError:
                absences[day] = [hour]
    return absences


def categories(idmap, node):
    c = node.get(_Categories)
    cat = {}
    if c:
        wf = False
        role = 0
        notcolliding = False
        ctag = False
        for w365id in c.split(LIST_SEP):
            cnode = idmap[w365id]
            wf_ = cnode["WorkloadFactor"]
            if wf_ != "1.0":
#TODO
                assert not wf
                wf = True
                cat["WorkloadFactor"] = float(wf_)
            if cnode["Colliding"] == "false":
                cat["NotColliding"] = "true"
            r = cnode["Role"]
            role |= int(r)

            sc = cnode["Shortcut"]
            if "_" in sc:    # only relevant for courses
#TODO
                assert not ctag
                ctag = True
                cat["Block"] = w365id
            try:    # only relevant for teachers
                _, n = sc.split("*")
            except ValueError:
                pass
            else:
#TODO
                assert not ctag
                ctag = True
                cat["MaxLunchDays"] = int(n)

        if role & 1:
            cat["CanSubstitute"] = "true"   # to mark a special subject as
                            # representing "available for substitutions"
        if role & 2:
            cat["NoReport"] = "true"        # Course with no report
        if role & 4:
            cat["NotRegistered"] = "true"   # Course with no register
                                            # (Klassenbuch) entry
        if role & 8:
            cat["WholeDayBlock"] = "true"   # for "Epoch" definitions
        if role & 16:
            cat["NoTeacher"] = "true"       # to mark a "dummy" teacher
        if notcolliding:
            cat["NotColliding"] = "true"

    return cat
