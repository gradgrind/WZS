"""
w365/wz_w365/make_schedule.py - last updated 2024-04-01

Given lesson times and room data, generate Schedule and Lesson entries
for Waldorf365.


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

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(basedir)

#from core.base import Tr
#T = Tr("w365.wz_w365.make_schedule)

### +++++

import uuid
from datetime import datetime


#TODO ...

from w365.wz_w365.w365base import (
    W365_DB,
    _Room,
    _Shortcut,
    _Name,
    _Id,
    _RoomGroup,
    _ListPosition,
    _capacity,
    LIST_SEP,
    absences,
    categories,
)


def get_uuid():
    return str(uuid.uuid4())

### -----


def make_schedule(
    container_id: str,
    placements: dict[str, dict],
    schedule_index0 = 100.0,
    lesson_index0 = 10000.0,
):
    date_time = datetime.today().isoformat().rsplit('.', 1)[0]
    lessons = []
    lesson_ids = []
    lesson_index = lesson_index0
    for aid, p in placements.items():
        length = int(p["Length"])
        cx = p["Course_x"]
        try:
            e, gl = cx.split("+", 1)
        except ValueError:
            # Normal course
            h = p["Period"]
            i = 1
            while True:
                lesson_index += 1.0
                lid = get_uuid()
                lesson_ids.append(lid)
                lessons.extend([
                    "*Lesson",
                    f"ContainerId={container_id}",
                    f'Course={cx}',
                    f'Day={p["Day"]}',
                    f'Hour={h}',
                    f'Fixed={p["Fixed"]}',
                    f"Id={lid}",
                    f"LastChanged={date_time}",     # 2024-03-30T18:59:53
                    f"ListPosition={lesson_index}",
#TODO
                    #f"LocalRooms={}", # 0b5413dc-1420-478f-b266-212fed8d2564
                    "",
                ])
                if i >= length:
                    break
                i += 1
                h = str(int(h) + 1)
        else:
            # Block (EpochPlan)
            for g in gl.split(","):
                h = p["Period"]
                i = 1
                while True:
                    lesson_index += 1.0
                    lid = get_uuid()
                    lesson_ids.append(lid)
                    lessons.extend([
                        "*Lesson",
                        f"ContainerId={container_id}",
                        f"EpochPlan={e}",
                        f"EpochPlanGrade={g}",
                        f'Day={p["Day"]}',
                        f'Hour={h}',
                        f'Fixed={p["Fixed"]}',
                        f"Id={lid}",
                        f"LastChanged={date_time}",     # 2024-03-30T18:59:53
                        f"ListPosition={lesson_index}",
#TODO
                        #f"LocalRooms={}", # 0b5413dc-1420-478f-b266-212fed8d2564
                        "",
                    ])
                    if i >= length:
                        break
                    i += 1
                    h = str(int(h) + 1)
    schedule_name = "fet001"
    schedule = [
        "*Schedule",
        f"ContainerId={container_id}",
        #f"End=",   #01. 03. 2024    # unused?
        f"Id={get_uuid()}",
        f"LastChanged={date_time}",     # 2024-03-30T18:59:53
        f"Lessons={'#'.join(lesson_ids)}",
        f"ListPosition={schedule_index0 + 1.0}",
        f"Name={schedule_name}",
        "NumberOfManualChanges=0",
        #f"Start=",  #01. 03. 2024  # unused?
        "YearPercent=1.0",
        "",
    ]

    schedule.extend(lessons)
    nl = "\n"
    return f'{nl.join(schedule)}'


'''
*Schedule
ContainerId=1d2a58cf-d882-422d-a8a8-fe5f5ed82a84
End=01. 03. 2024    # unused?
Id=b387a2a3-da72-4200-a05d-15e9f899cd2a
LastChanged=2024-03-30T12:28:34
Lessons=cc9a7028-0248-44b1-a3ff-34c4adae506b#df4a2602-1177-4992-a83a-7e6011435df2# ...

ListPosition=0.0    # get from existing Schedule entries
Name=fet00          # new name
NumberOfManualChanges=0
Start=01. 03. 2024  # unused?
YearPercent=1.0
'''

'''
*Lesson
ContainerId=1d2a58cf-d882-422d-a8a8-fe5f5ed82a84
Course=8d4ff396-69d5-492a-bb18-4752097c161e
Day=0
Fixed=false
Hour=2
Id=6ec9be89-50de-419b-a143-55205d7022b4
LastChanged=2024-03-30T18:59:53
ListPosition=1.0
LocalRooms=0b5413dc-1420-478f-b266-212fed8d2564

or, instead of Course:

EpochPlan=8626866f-9b99-4ea2-aa76-2b191ee11d7f
EpochPlanGrade=adddcb92-f8ee-43b8-baa5-de7021077e3b
'''

def read_activities(nodes):
    """Return a mapping,
        {fet-activity-id: (
                w365-Course-id or -EpochPlan-id,    (str)
                lesson-length                       (str)
            )
        }
    EpochPlan-ids have a "+" after the id, followed by a list of class
    references (","-separated).
    """
    amap = {}
    for node in nodes["Activities_List"]["Activity"]:
        w365idx = node["Comments"]
        if w365idx:
            amap[node["Id"]] = (w365idx, node["Duration"])
    return amap


def read_starting_times(nodes, activity_map):
    # First read days and periods
    daymap = {
        d["Name"]: str(i)
        for i, d in enumerate(nodes["Days_List"]["Day"])
    }
    #print("§DAYS:", daymap)
    periodmap = {
        p["Name"]: str(i)
        for i, p in enumerate(nodes["Hours_List"]["Hour"])
    }
    #print("§HOURS:", periodmap)
    ndata = {}
    t_constraints = nodes["Time_Constraints_List"]
    for node in t_constraints["ConstraintActivityPreferredStartingTime"]:
        aid = node["Activity_Id"]
        try:
            w365idx, length = activity_map[aid]
        except KeyError:
            continue
        #print("$$$", aid, "->", w365id)
        if node["Active"] != "true":
            continue
        ndata[aid] = {
            "Course_x": w365idx,
            "Length": length,
            "Day": daymap[node["Preferred_Day"]],
            "Period": periodmap[node["Preferred_Hour"]],
            "Fixed": node["Permanently_Locked"]
        }
    return ndata
'''
<ConstraintActivityPreferredStartingTime>
    <Weight_Percentage>100</Weight_Percentage>
    <Activity_Id>488</Activity_Id>
    <Preferred_Day>Di</Preferred_Day>
    <Preferred_Hour>A</Preferred_Hour>
    <Permanently_Locked>true</Permanently_Locked>
    <Active>true</Active>
    <Comments></Comments>
'''


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#


if __name__ == "__main__":
    import xmltodict
    from core.base import DATAPATH
    source = DATAPATH("fwsb_data_and_timetable.fet", "w365_data")
    with open(source, "r", encoding = "utf-8") as fh:
        xmlin = fh.read()
    data = xmltodict.parse(xmlin)
    container_id = data["fet"]["Comments"]
    print(f'\n******** {container_id} ***************')
    dtc = data["fet"]["Time_Constraints_List"]
    cst = dtc["ConstraintActivityPreferredStartingTime"]
    print(len(cst), cst[:10])
    activities = read_activities(data["fet"])
    print("\n-------------------------------------")
    print(len(activities), activities)
    print("\n=====================================")
    times = read_starting_times(data["fet"], activities)
    print(times)

    schedule = make_schedule(
        container_id,
        times,
        schedule_index0 = 100.0,
        lesson_index0 = 10000.0,
    )
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    out = DATAPATH("fwsb_extend", "w365_data")
    with open(out, "w", encoding = "utf-8") as fh:
        fh.write(schedule)
    print("  -->>", out)
