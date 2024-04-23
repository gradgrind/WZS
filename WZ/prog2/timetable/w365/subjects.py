"""
timetable/w365/subjects.py - last updated 2024-04-24

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

#from core.base import Tr
#T = Tr("timetable.w365.subjects")

### +++++

from timetable.w365.w365base import (
    _Subject,
    _Shortcut,
    _Name,
    _Id,
    _ListPosition,
    categories,
)

### -----


def read_subjects(w365_db):
    table = "SUBJECTS"
    _nodes = []
    for node in w365_db.scenario[_Subject]:
        id = node[_Shortcut]
        name = node[_Name]
        xnode = {"ID": id, "NAME": name}
        c = categories(w365_db.idmap, node)
        if c:
            xnode["EXTRA"] = c
        _nodes.append((float(node[_ListPosition]), node[_Id], xnode))
    w365id_nodes = []
    i = 0
    for _, _id, xnode in sorted(_nodes):
        i += 1
        xnode["#"] = i
        w365id_nodes.append((_id, xnode))
    # Add to database
    w365_db.add_nodes(table, w365id_nodes)
