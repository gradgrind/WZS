"""
w365/timeslots.py - last updated 2024-05_04

Manage time slots (for timetable).


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

#from core.wzbase import Tr
#T = Tr("w365.timeslots")

### +++++

from w365.w365base import (
    _Day,
    _Period,
    _Shortcut,
    _Name,
    _ListPosition,
    _Id,
    _Start,
    _End,
    _MiddayBreak,
    _FirstAfternoonHour,
)

### -----


def read_days(w365_db):
    table = "DAYS"
    w365id_nodes = []
    dlist = []
    for node in w365_db.scenario[_Day]:
        xnode = {
            "TAG": node.get(_Shortcut) or "",
            "NAME": node.get(_Name) or "",
        }
        dlist.append((int(float(node[_ListPosition])), node[_Id], xnode))
    dlist.sort()
    i = 0
    for _, _id, xnode in dlist:
        i += 1
        xnode["#"] = i
        xnode["ID"] = xnode["TAG"] or str(i)
        w365id_nodes.append((node[_Id], xnode))
    # Add to database
    w365_db.add_nodes(table, w365id_nodes)


def read_periods(w365_db):
    table = "PERIODS"
    w365id_nodes = []
    plist = []
    for node in w365_db.scenario[_Period]:
        xnode = {
            "TAG": node.get(_Shortcut) or "",
            "NAME": node.get(_Name) or "",
            "START_TIME": node[_Start],
            "END_TIME": node[_End],
            "_lb": node[_MiddayBreak] == "true",
            "_pm": node.get(_FirstAfternoonHour) == "true",
        }
        plist.append((int(float(node[_ListPosition])), node[_Id], xnode))
    plist.sort()
    i = 0
    lb = []
    w365_db.config1["LUNCHBREAK"] = lb
    for _, _id, xnode in plist:
        # These are 0-based indexes
        if xnode.pop("_lb"):
            lb.append(i)
        if xnode.pop("_pm"):
            w365_db.config1["AFTERNOON_START_PERIOD"] = i
        # These use 1-based indexes
        i += 1
        xnode["#"] = i
        xnode["ID"] = xnode["TAG"] or str(i)
        w365id_nodes.append((node[_Id], xnode))
    # Add to database
    w365_db.add_nodes(table, w365id_nodes)


#TODO: What about "time slots"? Perhaps these could be index pairs,
# like "2.5" (fifth lesson on Tuesday)?
