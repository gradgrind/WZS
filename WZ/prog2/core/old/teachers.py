"""
core/teachers.py - last updated 2024-02-26

Manage teacher data.

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

import sys, os

if __name__ == "__main__":
    # Enable package import if running as module
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(basedir)

#from core.base import Tr
#T = Tr("core.teachers")

### +++++

from core.basic_data import DB_Table

### -----


class Teachers(DB_Table):
    __slots__ = ()
    _table = "TEACHERS"
    order = "SORTNAME"
    null_entry = {
        "TID": "---", "FIRSTNAMES": "keine", "LASTNAME": "Lehrkraft",
        "SIGNED": "-----", "SORTNAME": "---"
    }

    @staticmethod
    def get_name(data):
        return f"{data.FIRSTNAMES} {data.LASTNAME}"

    def name(self, t_id):
        return self.get_name(self[t_id])

    def teacher_list(self, skip_null: bool = True):
        """Return an ordered list of teachers.
        """
        teachers = []
        for node in self.records():
            if (not skip_null) or (node.get("#") != "0"):
                teachers.append((node._id, node.TID, self.get_name(node)))
        return teachers


DB_Table.add_table(Teachers)


#TODO: Handle TT_TEACHERS table

# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import DB

    print("\n§Teachers:")
    table = DB("TEACHERS")
    for r in table.records():
        print("  --", r)

    print("\n -------------------------------")

    for r in table.teacher_list(skip_null = True):
        print("  --", r)
