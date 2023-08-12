#TODO ...
"""
timetable/tt_placement.py

Last updated:  2023-08-12

Handle the basic information for timetable display and processing.


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
    import sys, os
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import start
    start.setup(os.path.join(basedir, 'TESTDATA'))

#T = TRANSLATIONS("timetable.tt_placement")

### +++++

from core.basic_data import get_days, get_periods

### -----


class PlacementEngine:
    def __init__(self):

        return

#TODO: Reserve index 0 in TT_LESSONS for null/"empty"?

def data_structures(n_rooms):

    n_week_cells = len(get_days()) * len(get_periods())
    room_occupancy = [[0] * n_week_cells] * n_rooms # or [-1] ...
    week_placements = [0] * n_week_cells




# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from core.db_access import open_database
    open_database()

    from timetable.tt_base import read_tt_db
    tt_data, tt_lists = read_tt_db()
    tt_lessons, class_ttls, teacher_ttls = tt_lists

    print("ROOMS", len(tt_data.room_i), tt_data.room_i)
    data_structures(len(tt_data.room_i))
