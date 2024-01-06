"""
ui/dialogs/dialog_room_choice.py

Last updated:  2024-01-06

Supporting "dialog" for the course editor – select room(s).


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

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import Tr
T = Tr("ui.dialogs.dialog_room_choice")

### +++++

from typing import Optional

from core.base import REPORT_ERROR
from core.rooms import print_room_choice
from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    QDialogButtonBox,
    QTableWidgetItem,
    ### QtGui:
    ### QtCore:
    Qt,
    Slot,
    ### other
    load_ui,
)

NULL_ROOM = ([], 0)     # Representation of "no room chosen"

### -----

# Problem with starting all rooms with the same character:
# The jump-on-start-key(s) feature in the Qt table doesn't really work.
# Would it be OK to strip such a character off? Maybe not use it in the
# first place(!) – then if it helps at any place in the interface or
# timetable or whatever, add it in the display there.

"""Choose a list of rooms and (optionally) a single room-group.
An initial set of rooms can be supplied.
If the selection is the same as the initial set, an "OK" return
should be disabled.
A "Cancel" return (None) will indicate that no change is to be made.
Otherwise return a list (possibly empty) of rooms and (optionally)
a single room-group.
There is, additionally, a "Reset" return, which is a short-cut for
returning an empty choice.
"""

# Return a list of room indexes and a room-group index.
# The start-value is of the same form.
# Room 0 is possible only in courses which are restricted to a single class.
# This information would need to be passed in as <classroom>. Value 0 would
# indicate that no classroom is available.

def roomChoiceDialog(
    start_value: tuple,
    classroom: int,
    rooms: tuple,
    parent: Optional[QWidget] = None,
) -> Optional[tuple]:

    # <choices> is the list of "chosen" rooms: [ROOMS-id, ... ]
    # Note that this list can contain the special classroom entry (0) if
    # there is a classroom (parameter <classroom> != 0).
    # <current_value> combines the <choices> list with the TT_ROOM_GROUPS-id
    # of the additional room-group (0 => no extra rooms). It has the same
    # format as <start_value>, so they can be compared.

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = current_value

    @Slot()
    def reset():
        nonlocal current_value
        current_value = NULL_ROOM
        ui.accept()

    @Slot(int, int, int, int)
    def on_roomlist_currentCellChanged(row, col, row0, col0):
        """If an item in the room list is selected on the second column,
        reselect it on the first column.
        This causes the built-in search feature to work as intended –
        i.e. on the first letter(s) of the first column.
        """
        if col > 0:
            ui.roomlist.setCurrentCell(row, 0)

    ## Alternative:
    ##??? @Slot(QTableWidgetItem *, QTableWidgetItem *)
    #def on_roomlist_currentItemChanged(item, item0):
    #    if item.column() > 0:
    #        ui.roomlist.setCurrentCell(item.row(), 0)

    @Slot()
    def on_tb_add_clicked():
        row = ui.roomlist.currentRow()
        add_room_choice(room_list[row][0])
        write_choices()

    @Slot()
    def on_home_clicked():
        add_room_choice(0)
        write_choices()

    @Slot()
    def on_tb_bin_clicked():
        nonlocal choices
        row = ui.roomchoice.currentRow()
        if row >= 0:
            choices.pop(row)
            ui.roomchoice.removeRow(row)
            write_choices()

    @Slot(int)
    def on_room_groups_currentIndexChanged(i):
        if suppress_events: return
        nonlocal rgindex
        rgindex = i
        write_choices()

    @Slot()
    def on_tb_up_clicked():
        row = ui.roomchoice.currentRow()
        if row <= 0:
            return
        row1 = row - 1
        item = ui.roomchoice.takeItem(row, 0)
        ui.roomchoice.setItem(row, 0, ui.roomchoice.takeItem(row1, 0))
        ui.roomchoice.setItem(row1, 0, item)
        item = ui.roomchoice.takeItem(row, 1)
        ui.roomchoice.setItem(row, 1, ui.roomchoice.takeItem(row1, 1))
        ui.roomchoice.setItem(row1, 1, item)

        t = choices[row]
        choices[row] = choices[row1]
        choices[row1] = t
        write_choices()
        ui.roomchoice.selectRow(row1)

    @Slot()
    def on_tb_down_clicked():
        row = ui.roomchoice.currentRow()
        row1 = row + 1
        if row1 == len(choices):
            return
        item = ui.roomchoice.takeItem(row, 0)
        ui.roomchoice.setItem(row, 0, ui.roomchoice.takeItem(row1, 0))
        ui.roomchoice.setItem(row1, 0, item)
        item = ui.roomchoice.takeItem(row, 1)
        ui.roomchoice.setItem(row, 1, ui.roomchoice.takeItem(row1, 1))
        ui.roomchoice.setItem(row1, 1, item)

        t = choices[row]
        choices[row] = choices[row1]
        choices[row1] = t
        write_choices()
        ui.roomchoice.selectRow(row1)

    ##### functions #####

    def write_choices():
        """Write the current state to <current_value> and set the text field.
        """
        nonlocal current_value
        current_value = (choices, room_groups[rgindex][0])
        text = print_room_choice(
            current_value,
            rooms,
        )
        ui.roomtext.setText(text)
        # Compare with <start_value>
        pb_accept.setDisabled(current_value == start_value)

    def add_room_choice(room_id):
        """Append the room with given id to the choices table.
        """
        if room_id == 0:
            if not classroom:
                REPORT_ERROR(T("NO_CLASSROOM_DEFINED"))
                return
            if classroom in choices or 0 in choices:
                rid = room_list[classroom][1]
                cid = room_list[0][1]
                REPORT_ERROR(f'{T("CLASSROOM_ALREADY_CHOSEN")}: {cid}/{rid}')
                return
        elif room_id == classroom:
            if classroom in choices or 0 in choices:
                rid = room_list[room_id][1]
                cid = room_list[0][1]
                REPORT_ERROR(f'{T("CLASSROOM_ALREADY_CHOSEN")}: {cid}/{rid}')
                return
        elif room_id in choices:
            rid = room_list[room_id][1]
            REPORT_ERROR(f'{T("ROOM_ALREADY_CHOSEN")}: {rid}')
            return
        choices.append(room_id)
        # Get row in full room table
        row = room2line[room_id] # or classroom]?
        at_row = ui.roomchoice.rowCount()
        ui.roomchoice.insertRow(at_row)
        ui.roomchoice.setItem(at_row, 0, ui.roomlist.item(row, 0).clone())
        ui.roomchoice.setItem(at_row, 1, ui.roomlist.item(row, 1).clone())

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_room_choice.ui", None, locals())
    pb_reset = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Reset
    )
    pb_reset.clicked.connect(reset)
    pb_accept = ui.buttonBox.button(
        QDialogButtonBox.StandardButton.Ok
    )

    ### Data initialization

    ## Initial check of <start_value>
    try:
        rlist0, rg0 = start_value
        if start_value == NULL_ROOM:
            pb_reset.hide()
    except ValueError:
        rlist0, rg0 = NULL_ROOM
        if start_value is None:
            start_value = NULL_ROOM
            pb_reset.hide()

    ## Load the room and room-group tables
    room_list, room_groups = rooms
    room2line = {}
    n = len(room_list)
    ui.roomlist.setRowCount(n)
    for i, rdata in enumerate(room_list):
        id, rid, rname = rdata
        #print("§rdata:", rdata)
        if id == classroom:
            rid = f"{rid} ***"
            ui.home.setText(T("CLASSROOM", room = rid))
        room2line[id] = i
        item = QTableWidgetItem(rid)
        ui.roomlist.setItem(i, 0, item)
        item = QTableWidgetItem(rname)
        ui.roomlist.setItem(i, 1, item)
    ui.roomlist.hideRow(0)
    suppress_events = True
    ui.room_groups.clear()
    rglist = []
    rgindex = 0     # Initial index of room-group choice
    for i, rg in enumerate(room_groups):
        rglist.append(rg)
        if rg[0]:
            tooltip = ", ".join(room_list[room2line[r]][1] for r in rg[3])
            ui.room_groups.addItem(f"{rg[2]} ({rg[1]})")
            if rg0 == rg[0]:
                rgindex = i
        else:
            tooltip = "–––"
            ui.room_groups.addItem("")
        ui.room_groups.setItemData(
            i, tooltip, Qt.ItemDataRole.ToolTipRole
        )
    ui.room_groups.setCurrentIndex(rgindex)

    ### Set up initial room choice (from <start_val>)
    choices = []
    ui.roomchoice.setRowCount(0)
    for r in rlist0:
        add_room_choice(r)
    current_value = None
    result = None
    write_choices()
    suppress_events = False
    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    ui.home.setVisible(classroom > 0)
    ui.roomlist.selectRow(0)
    ui.roomlist.setFocus()
    ui.exec()
    return result


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":

    # Build simple room lists which don't depend on the database.
    all_rooms = [
        (0, "$", "(Klassenraum)"),
        (1, "01r", "Raum der 1. Klasse"),
        (2, "02r", "Raum der 2. Klasse"),
        (3, "03r", "Raum der 3. Klasse"),
        (4, "04r", "Raum der 4. Klasse"),
        (5, "Mu", "Musikraum"),
        (6, "Sp", "Sporthalle"),
    ]
    room_groups = [
        (0, "", "", ()),
        (1, "$$KR", "Klassenräume", [1,2,3,4]),
        (3, "$$AR", "allgemeine Räume", [3,4,5]),
    ]

    rooms = (all_rooms, room_groups)

    '''
    from core.basic_data import get_database
    db = get_database()
    from core.rooms import Rooms, RoomGroupMap, get_db_rooms
    rooms = get_db_rooms(Rooms(db), RoomGroupMap(db))
    '''

    print("----->", roomChoiceDialog(
        start_value = ([], 0),
        classroom = 1,
        rooms=rooms
    ))
    print("----->", roomChoiceDialog(
        start_value = ([1,2], 3),
        classroom = 0,
        rooms=rooms
    ))

