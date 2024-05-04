"""
core/subjects.py - last updated 2024-02-21

Manage subjects data.

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
    from core.base import setup
    setup(basedir)

#from core.base import Tr
#T = Tr("core.subjects")

### +++++

from core.basic_data import DB_Table

SUBJECT_SEP = '*'   # separator in subject name, before extra tag

### -----


class Subjects(DB_Table):
    __slots__ = ()
    _table = "SUBJECTS"
    order = "NAME"
    null_entry = {"SID": "", "NAME": "", "SORTING": ""}

    @staticmethod
    def clip_name(name: str) -> str:
        """Return the given subject name without the optional extra suffix.
        """
        return name.rsplit(SUBJECT_SEP, 1)[0]


DB_Table.add_table(Subjects)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import DB

    print("\n§Subjects:")
    subjects = DB("SUBJECTS")
    for r in subjects.records():
        print("  --", r)
