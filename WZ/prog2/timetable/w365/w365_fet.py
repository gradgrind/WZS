"""
timetable/w365/w365_fet.py - last updated 2024-04-20

Build a "fet" file from Waldorf365 data.


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
#T = Tr("timetable.w365.w365_fet")

### +++++

from timetable.w365.read_w365 import read_w365

###-----


def make_fet_file(data):
    print("\nTODO: make_fet_file")


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import DATAPATH

    dbpath = DATAPATH("db365.sqlite", "w365_data")
    #w365path = DATAPATH("test.w365", "w365_data")
    #w365path = DATAPATH("fwsb.w365", "w365_data")
    #w365path = DATAPATH("fms.w365", "w365_data")
    w365path = DATAPATH("fms_xep.w365", "w365_data")
    print("DATABASE FILE:", dbpath)
    print("W365 FILE:", w365path)

    w365db = read_w365(w365path)

#    w365db.save(dbpath)

    make_fet_file(w365db)
