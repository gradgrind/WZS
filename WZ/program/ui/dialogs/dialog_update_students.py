"""
ui/dialogs/dialog_update_students.py

Last updated:  2024-02-15

Supporting "dialog" for basic data – show and select updates to students
data.


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

import os
if __name__ == "__main__":
    import sys

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import Tr
T = Tr("ui.dialogs.dialog_update_students")

### +++++

from typing import Optional

from ui.ui_base import (
    ### QtWidgets:
    QTreeWidgetItem,

    QWidget,
    QStyledItemDelegate,
    QLineEdit,
    ### QtGui:
    ### QtCore:
    Qt,

    QPoint,
    Slot,
    QTimer,
    ### other
    SHOW_CONFIRM,
    Singleton,
)
from ui.table_support import Table, ListChoice
from core.base import DATAPATH, REPORT_ERROR
from core.basic_data import get_database, CONFIG
from core.classes import format_class_group, class_group_split
import grades.grade_tables  # noqa (load table "GRADE_REPORT_CONFIG")

from core.students import (
#    get_pupil_fields,
#    get_pupils,
#    pupil_data,
#    pupil_name,
    compare_update,
    update_classes,
)
#???
from local.local_pupils import get_sortname, get_remote_data

### -----


def updateStudentsDialog(
    pupils_delta,
    size,
    parent: Optional[QWidget] = None,
#TODO:
) -> Optional[tuple[str, str]]:     # return (occasion, class_group)
    usd = __UpdateStudentsDialog._get(parent)
    return usd.popup(pupils_delta, size)


class __UpdateStudentsDialog(Singleton):
    _ui_file = "dialog_edit_grade_table_selection.ui"

    def _setup(self):
        table_1 = Table(self.ui.report_table)
        self.report_table = ReportTable(table_1, self.update_report_type)

    def popup(
        self,
        pupils_delta,
        size,
    ):
        self.ui.tree.clear()
        # Divide changes according to class
        class_delta = {}
        for delta in pupils_delta:
            klass = delta[1]["CLASS"]
            try:
                class_delta[klass].append(delta)
            except KeyError:
                class_delta[klass] = [delta]
        # Localized field names
#???
        f_t = {line[0]: line[1] for line in CONFIG["PUPILS_FIELDS"]}
        # Populate the tree
        elements = []
        for klass, delta_list in class_delta.items():
            parent = QTreeWidgetItem(self.ui.tree)
            parent.setText(0, T["CLASS_K"].format(klass=klass))
            parent.setFlags(
                parent.flags()
                | Qt.ItemFlag.ItemIsAutoTristate
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            for delta in delta_list:
                child = QTreeWidgetItem(parent)
                elements.append((delta, child))
                child.setFlags(
                    child.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                op, pdata = delta[0], delta[1]
                name = pupil_name(pdata)
                if op == "NEW":
                    text = T["NEW_PUPIL_N"].format(name=name)
                elif op == "DELTA":
                    changes = delta[2]
                    if len(changes) > 1:
                        child.setFlags(
                            child.flags() | Qt.ItemFlag.ItemIsAutoTristate
                        )
                        for k, v in changes:
                            c2 = QTreeWidgetItem(child)
                            c2.setFlags(
                                c2.flags() | Qt.ItemFlag.ItemIsUserCheckable
                            )
                            c2.setText(0, f"{f_t[k]}[{v}]")
                            c2.setCheckState(0, Qt.Checked)
                        text = T["CHANGE_PUPIL_FIELDS"].format(name=name)
                    else:
                        k, v = changes[0]
                        text = T["CHANGE_PUPIL_FIELD"].format(
                            name=name, field=f"{f_t[k]}[{v}]"
                        )
                elif op == "REMOVE":
                    text = T["REMOVE_PUPIL_N"].format(name=name)
                else:
                    raise Bug(f"Unexpected pupil-delta operator: {op}")
                child.setText(0, text)
                child.setCheckState(0, Qt.Checked)
        # Show dialog and collect results
        keeplist = []
        dialog.resize(size)
        if dialog.exec():
            for delta, child in elements:
                # Filter the changes lists
                if child.checkState(0) == Qt.CheckState.Unchecked:
                    continue
                # Check update entries for children
                nchildren = child.childCount()
                if nchildren:
                    # Rewrite the updates list, including checked fields
                    ulist = delta[2]
                    field_list = ulist.copy()
                    ulist.clear()
                    for i in range(nchildren):
                        subc = child.child(i)
                        if subc.checkState(0) == Qt.CheckState.Checked:
                            ulist.append(field_list[i])
                keeplist.append(delta)
        return keeplist






#--
        self.occasion = occasion
        self.class_group = class_group
        self.class_group_list = []
        self.cgmap = {}
        self.report_types = {}
        self.occasions = []
        self.new_class_group = None
        self._groups = None
#        self.result = None

        # Data initialization
        self.suppress_events = True
        #    if title:
        #        ui.label.setText(title)
        #    ui.textline.setText(start_value or default)

        db = get_database()
        # Populate the class combobox
        class_list = db.table("CLASSES").class_list()
        class_list.reverse()
        self.ui.combo_classes.clear()
        self.ui.combo_classes.addItems(c for _, c, _ in class_list)
        # Configuration data
        self.init()
        self.suppress_events = False
        # Activate the dialog
        self.ui.resize(0, 0)
        if self.ui.exec():
            return (self.occasion, self.class_group)
        return None




#???
    def update_pupils(self):
        plist = get_remote_data()
        if not plist:
            return
        pupils_delta = compare_update(plist)
        if not pupils_delta:
            SHOW_INFO(T["NO_CHANGES"])
            return
        do_list = update_pupils_dialog(pupils_delta, self.pupil_table.size())
        if do_list:
        # Encapsulate the action in a "run block" (because it might
        # take a few moments)
            PROCESS(
                update_classes,
                T["DB_UPDATE_PUPILS"],
                changes=do_list
            )
            # Redisplay pupil list
            self.changed_class(self.klass)

