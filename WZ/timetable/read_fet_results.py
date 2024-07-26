


"""
read_fet_results.py - last updated 2024-07-26

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

#from datetime import datetime

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
        print("\n§DAYS:", self.days)

        self.hours = {
            h["Name"]: i
            for i, h in enumerate(data["Hours_List"]["Hour"])
        }
        print("\n§HOURS:", self.hours)

        self.classes = {}
        for node in data["Students_List"]["Year"]:
            dg = node["Comments"]
            glists = []
            if dg:
                for div in dg.split(DIV_SEP):
                    glists.append(div.split(GROUP_SEP))
            self.classes[node["Name"]] = glists
        print("\n§CLASSES:", self.classes)

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
        print("\n§ROOMS:", self.rooms)

        self.activities = {}
        for node in data["Activities_List"]["Activity"]:
            a = {
                'Teachers': node['Teacher'],
                'Subject': node['Subject'],
                'Students': node['Students'],
                'Duration': int(node['Duration']),
                'Active': node['Active'],
            }
            self.activities[int(node['Id'])] = a

        for node in data["Time_Constraints_List"]\
            ["ConstraintActivityPreferredStartingTime"]:
                a = self.activities[int(node["Activity_Id"])]
                a["Day"] = self.days[node["Preferred_Day"]]
                a["Hour"] = self.hours[node["Preferred_Hour"]]
                a["Fixed"] = node["Permanently_Locked"] == "true"

        for node in data["Space_Constraints_List"]\
            ["ConstraintActivityPreferredRoom"]:
                ai = int(node["Activity_Id"])
                a = self.activities[ai]
                a["Room"] = node["Room"]
                a["Real_Rooms"] = node.get("Real_Room") or []
                print(f"\n§ACTIVITY {ai:04d}: {a}")


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#


if __name__ == "__main__":
    import lib.xmltodict as xmltodict
#TODO: How to get the data???
    source = "test_data_and_timetable.fet"
    source = "test_data_1.fet"
    fet_data = FetData(source)
#    activities = read_activities(data)
