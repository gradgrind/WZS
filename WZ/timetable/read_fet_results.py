"""
read_fet_results.py - last updated 2024-07-28

Read the data from the result of a successful fet run.


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

GROUP_SEP = ","
DIV_SEP = "|"
CLASS_GROUP_SEP = "."

import lib.xmltodict as xmltodict

### -----


class FetData:
    def __init__(self, filepath):
        with open(filepath, "r", encoding = "utf-8") as fh:
            xmlin = fh.read()
        data = xmltodict.parse(xmlin)["fet"]

        self.days = {
            d["Name"]: i
            for i, d in enumerate(data["Days_List"]["Day"])
        }

        self.hours = {}
        for i, h in enumerate(data["Hours_List"]["Hour"]):
            ln, st_end = h["Long_Name"].split("@", 1)
            st, end = st_end.split("-", 1)
            self.hours[h["Name"]] = {
                "index": i,
                "start": st,
                "end": end,
            }

        self.classes = {}
        for node in data["Students_List"]["Year"]:
            dg = node["Comments"]
            glists = []
            if dg:
                for div in dg.split(DIV_SEP):
                    glists.append(div.split(GROUP_SEP))
            self.classes[node["Name"]] = glists

        self.rooms = {}
        for node in data["Rooms_List"]["Room"]:
            rr = []
            if node["Virtual"] == "true":
                for rrset in node["Set_of_Real_Rooms"]:
                    rr.append(rrset["Real_Room"])
            self.rooms[node["Name"]] = {
                "LongName": node["Long_Name"] or "",
                "RoomGroups": rr,
            }

        self.teachers = {
            node["Name"]: node["Long_Name"] or node["Comments"]
            for node in data["Teachers_List"]["Teacher"]
        }

        self.activities = {}
        for node in data["Activities_List"]["Activity"]:
            #TODO: Is it possible that there is no "Teacher" field?
            t = node["Teacher"]
            if t:
                if not isinstance(t, list):
                    t = [t]
            else:
                t = []
            #TODO: Is it possible that there is no "Students" field?
            s = node["Students"]
            if s:
                if not isinstance(s, list):
                    s = [s]
            else:
                #TODO: Is this possible?
                s = []
            a = {
                "Teachers": t,
                "Subject": node["Subject"],
                "Students": s,
                "Duration": int(node["Duration"]),
                "Active": node["Active"],
            }
            self.activities[int(node['Id'])] = a

        for node in data["Time_Constraints_List"]\
            ["ConstraintActivityPreferredStartingTime"]:
                a = self.activities[int(node["Activity_Id"])]
                a["Day"] = self.days[node["Preferred_Day"]]
                a["Hour"] = self.hours[node["Preferred_Hour"]]["index"]
                a["Fixed"] = node["Permanently_Locked"] == "true"

        for node in data["Space_Constraints_List"]\
            ["ConstraintActivityPreferredRoom"]:
                ai = int(node["Activity_Id"])
                a = self.activities[ai]
                a["Room"] = node["Room"]
                a["Real_Rooms"] = node.get("Real_Room") or []


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#


if __name__ == "__main__":
#TODO: How to get the data???
    source = "test_data_and_timetable.fet"
    source = "test_data_1.fet"
    fet_data = FetData(source)
    print("\n§DAYS:", fet_data.days)
    print("\n§HOURS:", fet_data.hours)
    print("\n§CLASSES:", fet_data.classes)
    print("\n§ROOMS:", fet_data.rooms)
    for ai, a in fet_data.activities.items():
        print(f"\n§ACTIVITY {ai:04d}: {a}")
