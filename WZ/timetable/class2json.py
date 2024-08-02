"""
show_class.py

Last updated:  2024-08-02

Prepare a json file for timetable display purposes with the lessons of a class.


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

### +++++

import json

from read_fet_results import FetData
from view_part_info import ViewPartInfo

### -----


def prepare_classes(data, show_fixed = False):
    class_data = {}
    for klass in data.data.classes:
        activities = data.class_activities[klass]
        klist = []
        class_data[klass] = klist
        for ai in activities:
            a = data.data.activities[ai]
            for o, l, t, gl in a["Class_Tiles"][klass]:
                rrooms = a["Real_Rooms"]
                if rrooms:
                    if len(rrooms) > 6:
                        room = ",".join(rrooms[:5]) + " ..."
                    else:
                        room = ",".join(rrooms)
                else:
                    room = a["Room"]
                tlist = a["Teachers"]
                if len(tlist) > 6:
                    teacher = ",".join(tlist[:5]) + " ..."
                else:
                    teacher = ",".join(tlist)
                klist.append({
                    "day": a["Day"],
                    "hour": a["Hour"],
                    "duration": a["Duration"],
                    "fraction": l,
                    "offset": o,
                    "total": t,
                    "centre":  a["Subject"],
                    "tl": teacher,
                    "tr": ",".join(gl),
                    "br": room,
                    "bl": "!" if show_fixed and a["Fixed"] else ""
                })
    return class_data


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
#    from ui_base import init_app, run
#    init_app()

#TODO: How to get the data???
    source = "test_data_and_timetable.fet"
    #source = "test_data_1.fet"
    fet_data = FetData(source)
    #print("\n§DAYS:", fet_data.days)
    #print("\n§HOURS:", fet_data.hours)
    #print("\n§CLASSES:", fet_data.classes)
    #print("\n§ROOMS:", fet_data.rooms)
    #for ai, a in fet_data.activities.items():
    #    print(f"\n§ACTIVITY {ai:04d}: {a}")

    clview = ViewPartInfo(fet_data)

    class_list = []
    jsondata = {
        "Title": "Stundenpläne der Klassen",
        "School": "Freie Michaelschule",
        "Pages": class_list,
    }
    for k, kitems in prepare_classes(clview).items():
        class_list.append([f"Klasse {k}", kitems])
    ofile = source.rsplit(".", 1)[0] + ".json"
    with open(ofile, "w", encoding = "utf-8") as fh:
        json.dump(jsondata, fh)
    print(f"\n  Wrote data to '{ofile}'")
    print("\nProcess the output file with:")
    print(f"typst compile --input ifile={ofile} print_timetable.typ")
