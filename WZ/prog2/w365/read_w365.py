"""
w365/read_w365.py - last updated 2024-05-04

Read timetable-relevant data from Waldorf365 dump file.


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
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.wzbase import setup
    setup(basedir)

#from core.base import Tr
#T = Tr("w365.read_w365")

### +++++

from w365.w365base import W365_DB, read_active_scenario
from w365.rooms import read_rooms
from w365.subjects import read_subjects
from w365.teachers import read_teachers
from w365.class_groups import read_groups
from w365.activities import read_activities
from w365.timeslots import read_days, read_periods

###-----


def read_w365(filepath):
    filedata = read_active_scenario(filepath)
    w365 = W365_DB(filedata)

    print("\nTODO: UserConstraints:")
    for i in filedata["$$SCENARIO"]["UserConstraint"]:
        print(" ---", i)
    print("\n  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
    #quit(2)

    read_days(w365)
    read_periods(w365)
    read_groups(w365)
    read_subjects(w365)
    read_teachers(w365)
    read_rooms(w365)
    read_activities(w365)
    # Add config items to database
    w365.config2db()
    return w365


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.wzbase import DATAPATH

    #w365path = DATAPATH("test.w365", "w365_data")
    #w365path = DATAPATH("fwsb.w365", "w365_data")
    #w365path = DATAPATH("fms.w365", "w365_data")
    w365path = DATAPATH("fwsb2.w365", "w365_data")

    #w365path = DATAPATH("fms_xep.w365", "w365_data")

    print("W365 FILE:", w365path)

    w365db = read_w365(w365path)

    w365db.save()
